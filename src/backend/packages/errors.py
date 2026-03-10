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
        Divide rows where Start Hours and End Hours are between
        two different months.
    """

    df = df.copy()

    df["Start Hours"] = pd.to_datetime(df["Start Hours"], errors="coerce")
    df["End Hours"] = pd.to_datetime(df["End Hours"], errors="coerce")

    year_month = df['YearMonth'].astype(str)

    if len(year_month.unique()) == 1:
        month_start = pd.to_datetime(year_month.iloc[0])
        next_month = month_start + pd.offsets.MonthBegin(1)    

        mask = df["End Hours"] > next_month

        # Extract first and apply reset on Start Hours
        df1 = df.loc[mask].copy()

        # Second part
        df1["Start Hours"] = next_month
        df1["DowntimeHours"] = (
            df1["End Hours"] - df1["Start Hours"]
        ).dt.total_seconds() / 3600

        # first part
        df.loc[mask, "End Hours"] = next_month
        df.loc[mask, "DowntimeHours"] = (
            df.loc[mask, "End Hours"] - df.loc[mask, "Start Hours"]
        ).dt.total_seconds() / 3600

        df = pd.concat([df, df1], ignore_index= True)

    return df


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