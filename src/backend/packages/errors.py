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
        df["Start Hours"], errors="coerce", dayfirst=True
    )
    df["End Hours"] = pd.to_datetime(
        df["End Hours"], errors="coerce", dayfirst=True
    )

    original_year_month = pd.to_datetime(
        df["YearMonth"].astype(str),
        errors="coerce",
        dayfirst=True
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
# 
# =======================================================
def get_invalid_start_month_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return rows where month 'Start Hours'is different
    to 'YearMonth' and to 'YearMonth + 1'.
    """

    df = df.copy()

    # Conversion
    df["Start Hours"] = pd.to_datetime(df["Start Hours"], errors="coerce")
    year_month = pd.to_datetime(df["YearMonth"].astype(str), errors="coerce")

    # Start Hours month (Brought back to month 1st)
    start_month = df["Start Hours"].values.astype("datetime64[M]")

    # YearMonth and YearMonth + 1
    ym = year_month.values.astype("datetime64[M]")
    ym_plus_1 = (year_month + pd.offsets.MonthBegin(1)).values.astype("datetime64[M]")

    # Condition : different of both
    mask = (start_month != ym) & (start_month != ym_plus_1)

    return (
        df.loc[~mask].reset_index(drop=True),  # valid
        df.loc[mask].reset_index(drop=True)    # unvalid
    )


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
# 
# =======================================================
def correct_imbricated_period(
    df: pd.DataFrame,
    subset_cols: list[str],
    start_col: str = "Start Hours",
    end_col: str = "End Hours"
) -> pd.DataFrame:
    """
    Corrige les périodes imbriquées.

    Règle :
        - une intervention qui démarre plus tard est prioritaire.
        - les anciennes sont raccourcies ou découpées.

    Retourne un DataFrame sans chevauchement.
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
# 
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
