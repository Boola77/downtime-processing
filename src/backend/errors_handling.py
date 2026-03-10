# coding:utf-8

import pandas as pd
from typing import TypedDict

from backend.packages.filtering import *
from backend.packages.errors import *

# ----------------- TypedDicts for error checks -----------------
class DuplicateCheck(TypedDict):
    subset: str | list[str]

class OutlierCheck(TypedDict):
    column: str
    low: float
    high: float

class NaNCheck(TypedDict):
    subset: str | list[str]


# ----------------- Orchestrator -----------------
def errors_handling(
        df: pd.DataFrame,
        duplicate_columns: DuplicateCheck | None = None,
        nan_columns: NaNCheck | None = None,
        outlier_columns: OutlierCheck | None = None,
        downtime: bool = False
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
        Analyze common errors and return clean data + dict of error DataFrames.
    """

    df = df.copy()

    errors: dict[str, pd.DataFrame] = {}

    # ---------- DUPLICATES ----------
    if duplicate_columns:
        subset = duplicate_columns["subset"]
        max_nan = duplicate_columns.get("max_nan", 2)

        duplicated_rows = detect_duplicates(
            df,
            subset,
            max_nan= max_nan
        )
        df = df.drop(duplicated_rows.index)
        errors["duplicates"] = duplicated_rows.reset_index(drop=True)

    # ---------- NaNs ----------
    if nan_columns:
        nan_rows = detect_nans(
            df,
            nan_columns['subset']
        )
        df = df.drop(nan_rows.index)
        errors["missing_values"] = nan_rows.reset_index(drop=True)

    # ---------- OUTLIERS ----------
    if outlier_columns:
        outlier_rows = detect_outliers(
            df,
            outlier_columns['column'],
            outlier_columns['low'],
            outlier_columns['high']
        )
        df = df.drop(outlier_rows.index)
        errors["outliers"] = outlier_rows.reset_index(drop=True)

    # ---------- DOWNTIME ----------
    if downtime:
        df = convert_to_datetime(df, ["Start Hours", "End Hours"])
     
        mismatch = downtime_hrs_mismatch(df)
        df = df.drop(mismatch.index)
        errors["downtime_mismatch"] = mismatch.reset_index(drop=True)

        df = reset_exceed_end_time(df)
    
    df = df.reset_index(drop= True)

    return df, errors