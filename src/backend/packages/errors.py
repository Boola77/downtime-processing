# coding:utf-8

import pandas as pd
from typing import TypedDict

# ----------------- TypedDicts for error checks -----------------
class DuplicateCheck(TypedDict):
    subset: str | list[str]

class OutlierCheck(TypedDict):
    column: str
    low: float
    high: float

class NaNCheck(TypedDict):
    subset: str | list[str]


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


def reset_exceed_end_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split rows where Start Hours and End Hours span across two months
    so that no DowntimeHours crosses a month boundary.
    """

    df = df.copy()

    df["Start Hours"] = pd.to_datetime(df["Start Hours"], errors="coerce")
    df["End Hours"] = pd.to_datetime(df["End Hours"], errors="coerce")

    # Beginning of month based on Start Hours
    df["month_start"] = df["Start Hours"].values.astype("datetime64[M]")
    df["next_month"] = df["month_start"] + pd.offsets.MonthBegin(1)

    # Rows that spill over into the next month
    mask = df["End Hours"] > df["next_month"]

    # ---- Slice 1 (Current motnh) ----
    df_current = df.copy()
    df_current.loc[mask, "End Hours"] = df_current.loc[mask, "next_month"]

    df_current["DowntimeHours"] = (
        df_current["End Hours"] - df_current["Start Hours"]
    ).dt.total_seconds() / 3600

    # ---- Slice 2 (Next month) ----
    df_next = df.loc[mask].copy()
    df_next["Start Hours"] = df_next["next_month"]

    df_next["DowntimeHours"] = (
        df_next["End Hours"] - df_next["Start Hours"]
    ).dt.total_seconds() / 3600

    # Concat
    df_final = pd.concat([df_current, df_next], ignore_index=True)

    # Cleaning
    df_final = df_final.drop(columns=["month_start", "next_month"])

    return df_final


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


def detect_negative_values(
        df: pd.DataFrame,
        column: str
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return two DataFrames:
        1. rows without negative values in the column
        2. rows with negative values in the column
    """

    df = df.copy()

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")
    
    mask = df[column] < 0

    df_positive = df.loc[~mask].reset_index(drop=True)
    df_negative = df.loc[mask].reset_index(drop=True)

    return df_positive, df_negative