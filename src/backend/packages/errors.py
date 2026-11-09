# coding:utf-8
import pandas as pd


# =======================================================
# détecte des doublons "métier" avec NaN comme joker
# =======================================================
def detect_duplicates(
        df: pd.DataFrame,
        columns: str | list[str],
        max_nan: int = 2
    ) -> pd.DataFrame:
    """
    Detect duplicates where:
    - NaN acts as wildcard
    - rows with more than max_nan NaN are ignored
    """

    df = df.copy()

    if isinstance(columns, str):
        columns = [columns]

    # Keep only rows enough full
    nan_count = df[columns].isna().sum(axis=1)
    valid_df = df[nan_count <= max_nan]

    if len(valid_df) < 2:
        return df.iloc[0:0]

    # Create a partial key (NaN = wildcard)
    data = valid_df[columns].astype("string")

    keys = (
        data
        .where(data.notna(), "")
        .agg("|".join, axis=1)
    )

    # Detect groups > 1
    dup_idx = keys[keys.duplicated(keep=False)].index

    return df.loc[dup_idx]


# =======================================================
# détecte les valeurs manquantes
# =======================================================
def detect_nans(
        df: pd.DataFrame,
        columns: str | list[str]
    ) -> pd.DataFrame:
    """Return rows with NaN in any of the subset columns."""

    df = df.copy()

    if isinstance(columns, str):
        mask = df[columns].isna()
    else:
        mask = df[columns].isna().any(axis=1)

    return df[mask]


# =======================================================
# vérifie la cohérence durée = End - Start
# =======================================================
def downtime_hrs_mismatch(
        df: pd.DataFrame,
        tolerance_minutes: int = 10
    ) -> pd.DataFrame:
    """
        Checking downtime hours is correct
    """

    df = df.copy()

    expected_end = pd.to_datetime(df["Start Hours"]) + pd.to_timedelta(
        df["DowntimeHours"], unit="h"
    )

    diff_minutes = (
        (expected_end - pd.to_datetime(df["End Hours"]))
        .dt.total_seconds()
        .abs() / 60
    )

    return df[diff_minutes > tolerance_minutes]


# =======================================================
# 
# =======================================================
def reset_exceed_end_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split intervals at every month boundary and at 06:30
    immediately following each month boundary.

    Preserve the original YearMonth until the 06:30 boundary.
    Recalculate DowntimeHours for every generated segment.
    """

    df = df.copy()

    # Dates au format jour/mois/année
    df["Start Hours"] = pd.to_datetime(
        df["Start Hours"], errors="coerce", dayfirst=False
    )
    df["End Hours"] = pd.to_datetime(
        df["End Hours"], errors="coerce", dayfirst=False
    )

    original_year_month = pd.to_datetime(
        df["YearMonth"].astype(str),
        errors="coerce",
        dayfirst=False
    )

    result = []

    for pos in range(len(df)):
        row = df.iloc[pos].copy()

        start = row["Start Hours"]
        end = row["End Hours"]
        reference = original_year_month.iloc[pos]

        # Conserver les lignes invalides sans modification
        if (
            pd.isna(start)
            or pd.isna(end)
            or pd.isna(reference)
            or end <= start
        ):
            result.append(row)
            continue

        cursor = start
        current_year_month = row["YearMonth"]

        def append_segment(segment_start, segment_end, year_month):
            """Add a segment and recalculate its duration."""
            if segment_end <= segment_start:
                return

            segment = row.copy()
            segment["Start Hours"] = segment_start
            segment["End Hours"] = segment_end
            segment["YearMonth"] = year_month
            segment["DowntimeHours"] = (
                segment_end - segment_start
            ).total_seconds() / 3600

            result.append(segment)

        while cursor < end:

            # Prochaine frontière mensuelle
            month_boundary = (
                cursor.to_period("M") + 1
            ).start_time

            # Si l'intervalle traverse la fin du mois
            if cursor < month_boundary < end:

                # 1. Segment jusqu'à minuit
                append_segment(
                    cursor,
                    month_boundary,
                    current_year_month
                )

                # 2. Frontière de changement d'équipe à 06:30
                shift_boundary = (
                    month_boundary
                    + pd.Timedelta(hours=6, minutes=30)
                )

                if end <= shift_boundary:
                    # L'intervalle s'arrête avant ou à 06:30
                    append_segment(
                        month_boundary,
                        end,
                        current_year_month
                    )
                    break

                # Segment entre minuit et 06:30 :
                # conserver le YearMonth précédent
                append_segment(
                    month_boundary,
                    shift_boundary,
                    current_year_month
                )

                # 3. Après 06:30, affecter la nouvelle date
                cursor = shift_boundary
                current_year_month = shift_boundary.normalize()

            else:
                # Aucun autre changement de mois avant la fin.
                # Si l'intervalle commence exactement à minuit
                # le premier jour d'un mois, appliquer aussi 06:30.
                is_month_start = (
                    cursor.day == 1
                    and cursor == cursor.normalize()
                )

                if is_month_start:
                    shift_boundary = (
                        cursor + pd.Timedelta(
                            hours=6, minutes=30
                        )
                    )

                    if cursor < shift_boundary < end:
                        append_segment(
                            cursor,
                            shift_boundary,
                            current_year_month
                        )

                        cursor = shift_boundary
                        current_year_month = cursor.normalize()
                        continue

                append_segment(
                    cursor,
                    end,
                    current_year_month
                )
                break

    return pd.DataFrame(result).reset_index(drop=True)


# =======================================================
# détecte des valeurs hors bornes
# =======================================================
def detect_outliers(
        df: pd.DataFrame,
        column: str,
        low_value: float,
        high_value: float
    ) -> pd.DataFrame:
    """Return rows where column values are outside [low, high]."""

    df = df.copy()
    
    mask = (df[column] < low_value) | (df[column] > high_value)
    return df[mask]


# =======================================================
# Correction of overlapping Labor periods
# =======================================================
def correct_imbricated_period(
        df: pd.DataFrame,
        subset_cols: list[str],
        start_col: str = "Start Hours",
        end_col: str = "End Hours"
    ) -> pd.DataFrame:
    """
    Correct overlapping time periods.

    Rule :
        - An intervention that starts laters priority.
        - Earlier interventions are shortened or split.

    Retourn a DataFrame with no overlaps.
    """

    df = df.copy()
    df["_modified"] = False

    df[start_col] = pd.to_datetime(df[start_col])
    df[end_col] = pd.to_datetime(df[end_col])

    corrected = []

    for _, group in df.groupby(subset_cols):

        group = group.sort_values(start_col)

        result = []

        for _, current in group.iterrows():

            current_start = current[start_col]
            current_end = current[end_col]

            new_result = []

            overlap_found = False

            for _, old in pd.DataFrame(result).iterrows() if len(result) else []:

                old_start = old[start_col]
                old_end = old[end_col]

                # Aucun chevauchement
                if old_end <= current_start or old_start >= current_end:
                    new_result.append(old)
                    continue

                overlap_found = True

                # Ancienne période avant la nouvelle
                if old_start < current_start:
                    left = old.copy()
                    left[end_col] = current_start
                    left["_modified"] = True

                    if left[start_col] < left[end_col]:
                        new_result.append(left)

                # Ancienne période après la nouvelle
                if old_end > current_end:
                    right = old.copy()
                    right[start_col] = current_end
                    right["_modified"] = True

                    if right[start_col] < right[end_col]:
                        new_result.append(right)            
                
            current = current.copy()
            current["_modified"] = overlap_found

            new_result.append(current)

            result = sorted(
                new_result,
                key=lambda x: x[start_col]
            )

        corrected.extend(result)

    corrected = pd.DataFrame(corrected)

    corrected = corrected.sort_values(
        subset_cols + [start_col]
    ).reset_index(drop=True)

    # Recalcul de la durée en heures
    mask = corrected["_modified"]

    corrected.loc[mask, "DowntimeHours"] = (
        (
            corrected.loc[mask, end_col]
            - corrected.loc[mask, start_col]
        ).dt.total_seconds() / 3600
    )
    corrected = corrected.drop(columns="_modified")

    return corrected


# =======================================================
# Identification of overlapping Labor periods
# =======================================================
def detect_imbricated_period(
        df: pd.DataFrame,
        subset_cols: list[str],
        start_col: str = "Start Hours",
        end_col: str = "End Hours"
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
        Split dataframe into:
        - clean rows
        - rows with duplicates (including time inclusion)

        Duplicates are defined as:
        - same values on subset_cols (excluding timestamps)
        - AND identical or nested time intervals

        Returns:
            df_clean, df_anomalies
    """
 
    df = df.copy()

    # Sécuriser les types datetime
    df[start_col] = pd.to_datetime(df[start_col])
    df[end_col] = pd.to_datetime(df[end_col])

    group_cols = [col for col in subset_cols if col not in [start_col, end_col]]

    rows_flagged = set()

    for _, group in df.groupby(group_cols):
        group = group.sort_values(start_col)
        indices = group.index.tolist()

        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                idx_i = indices[i]
                idx_j = indices[j]

                start_i, end_i = df.loc[idx_i, [start_col, end_col]]
                start_j, end_j = df.loc[idx_j, [start_col, end_col]]

                # Inclusion ou égalité
                overlap = (
                    (start_i <= start_j and end_i >= end_j) or
                    (start_j <= start_i and end_j >= end_i)
                )

                if overlap:
                    rows_flagged.add(idx_i)
                    rows_flagged.add(idx_j)

    df_anomalies = df.loc[list(rows_flagged)].reset_index(drop=True)
    df_clean = df.drop(index=rows_flagged).reset_index(drop=True)

    return df_clean, df_anomalies



def correct_shift_period(
        df: pd.DataFrame,
        start_col: str = "Start Hours",
        end_col: str = "End Hours",
        yearmonth_col: str = "YearMonth",
        downtime_col: str = "DowntimeHours"
    ) -> pd.DataFrame:

    df = df.copy()

    df[start_col] = pd.to_datetime(df[start_col])
    df[end_col] = pd.to_datetime(df[end_col])

    # Détection du format dominant de YearMonth
    formats = df[yearmonth_col].dropna().astype(str)

    date_format = (
        formats.str.len().mode().iloc[0] >= 10
    )

    corrected = []

    for _, row in df.iterrows():

        start = row[start_col]
        end = row[end_col]

        if pd.isna(start) or pd.isna(end) or end <= start:
            corrected.append(row.copy())
            continue

        boundaries = set()

        # Découpage à minuit lors d'un changement de mois
        current = start.normalize() + pd.Timedelta(days=1)

        while current < end:

            if current.month != (current - pd.Timedelta(days=1)).month:
                boundaries.add(current)

            current += pd.Timedelta(days=1)

        # Découpage à 07:00 le lendemain du changement de mois
        current = start.normalize()

        while current < end:

            next_day = current + pd.Timedelta(days=1)

            if next_day.month != current.month:

                shift_boundary = (
                    next_day + pd.Timedelta(hours=7)
                )

                if start < shift_boundary < end:
                    boundaries.add(shift_boundary)

            current = next_day

        points = [start] + sorted(boundaries) + [end]

        for segment_start, segment_end in zip(
            points[:-1], points[1:]
        ):

            new_row = row.copy()

            new_row[start_col] = segment_start
            new_row[end_col] = segment_end

            # La date du shift est celle du jour à 07:00
            # Une heure avant 07:00 appartient au shift précédent
            shift_date = (
                segment_start - pd.Timedelta(hours=7)
            ).normalize()

            if date_format:
                new_row[yearmonth_col] = shift_date.strftime(
                    "%Y-%m-%d"
                )
            else:
                new_row[yearmonth_col] = shift_date.strftime(
                    "%Y-%m"
                )

            new_row[downtime_col] = (
                segment_end - segment_start
            ).total_seconds() / 3600

            corrected.append(new_row)

    result = pd.DataFrame(corrected)

    result = result.sort_values(
        start_col
    ).reset_index(drop=True)

    return result

# =======================================================
# YearMonth of Labor
# =======================================================
def correct_yearmonth(
        df: pd.DataFrame,
        yearmonth_col: str ="YearMonth",
        start_col: str = "Start Hours",
        end_col: str = "End Hours",
        duration_col: str = "DowntimeHours"
    ) -> pd.DataFrame:

    df = df.copy()

    df[start_col] = pd.to_datetime(df[start_col])
    df[end_col] = pd.to_datetime(df[end_col])

    # Detection of the dominant format
    values = df[yearmonth_col].dropna().astype(str)

    daily_count = values.str.match(
        r"^\d{4}-\d{2}-\d{2}$"
    ).sum()

    monthly_count = values.str.match(
        r"^\d{4}-\d{2}$"
    ).sum()

    daily_format = daily_count > monthly_count

    corrected = []

    for _, row in df.iterrows():

        start = row[start_col]
        end = row[end_col]

        if pd.isna(start) or pd.isna(end) or end <= start:
            corrected.append(row)
            continue

        # Start Shift DATE
        shift_date = (start - pd.Timedelta(hours=6)).date()

        # Check if the labor crosses many month
        crosses_month = (
            start.year != end.year
            or start.month != end.month
        )

        # Funtion to determine YearMonth
        def get_yearmonth(date):
            if daily_format:
                return pd.Timestamp(date).strftime("%Y-%m-%d")
            return pd.Timestamp(date).strftime("%Y-%m")
        
        # Case 1: same month -> no split
        if not crosses_month:

            row = row.copy()
            row[yearmonth_col] = get_yearmonth(shift_date)

            corrected.append(row)
            continue

        # Case 2: Many months -> Split
        boundaries = []

        current_day = start.normalize()

        while current_day <= end.normalize():

            midnight = current_day
            shift_change = current_day + pd.Timedelta(hours=6)

            for boundary in [midnight, shift_change]:

                if start < boundary < end:

                    # Split if only the frontier is month changing
                    before = boundary - pd.Timedelta(nanoseconds=1)

                    if (
                        before.year != boundary.year
                        or before.month != boundary.month
                    ):
                        boundaries.append(boundary)

            current_day += pd.Timedelta(days=1)

        points = [start] + sorted(set(boundaries)) + [end]

        for i in range(len(points) - 1):

            segment_start = points[i]
            segment_end = points[i + 1]

            segment = row.copy()

            segment[start_col] = segment_start
            segment[end_col] = segment_end

            segment_shift_date = (
                segment_start - pd.Timedelta(hours=6)
            ).date()

            segment[yearmonth_col] = get_yearmonth(
                segment_shift_date
            )

            segment[duration_col] = (
                segment_end - segment_start
            ).total_seconds() / 3600

            corrected.append(segment)

    result = pd.DataFrame(corrected)

    return result.reset_index(drop=True)