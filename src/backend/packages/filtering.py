# coding:utf-8

import pandas as pd
import numpy as np
from typing import NamedTuple


class BrowserMapping(NamedTuple):
    df_key: str
    df_target: str
    browser_key: str
    browser_value: str


def create_template(
        filepath: str,
        template: str
    ) -> pd.DataFrame:
    """Create an empty DataFrame using the template columns."""

    # ------- Read operating data template ----------
    if template.lower() == 'operating':
        df = pd.read_excel(filepath, sheet_name= "operating")
        return pd.DataFrame(columns= df.columns)
    
    # ------- Read downtime data template ----------
    if template.lower() == 'downtime':
        df = pd.read_excel(filepath, sheet_name= "downtime")
        return pd.DataFrame(columns= df.columns)
        
    else:
        raise ValueError(f"Unknown template type: {template}")


def fill_columns(
        df: pd.DataFrame,
        df_source: pd.DataFrame,
        selected_columns: dict
    ) -> pd.DataFrame:
    """Fill target columns from source DataFrame."""

    df = df.copy()
    df_source = df_source.copy()

    target_cols = list(selected_columns.keys())
    source_cols = list(selected_columns.values())

    missing = set(source_cols) - set(df_source.columns)
    if missing:
        raise KeyError(f"Missing columns in source: {target_cols} and {source_cols}")

    df[target_cols] = df_source[source_cols].values

    return df


def filter_existing_equipment(
        df: pd.DataFrame,
        equipment_browser: pd.DataFrame,
        equip_column: dict
    ) -> pd.DataFrame:
    """Keep only rows where 'Equipment' exists in the equipment browser."""

    df = df.copy()
    equipment_browser = equipment_browser.copy()

    target, value = next(iter(equip_column.items()))
    
    # if len(value) != 1: 
    #     raise ValueError("Expected exactly one equipment name mapping")

    mask = df[target].isin(equipment_browser[value].dropna())
    return df.loc[mask].reset_index(drop=True)


def assign_model(
        df: pd.DataFrame,
        equipment_browser: pd.DataFrame,
        mapping: BrowserMapping
    ) -> pd.DataFrame:
    """
    Assign model to df based on equipment number mapping.
    """

    df = df.copy()
    equipment_browser = equipment_browser.copy()

    missing = {
        "df_key": mapping.df_key not in df.columns,
        "df_target": mapping.df_target not in df.columns,
        "browser_key": mapping.browser_key not in equipment_browser.columns,
        "browser_value": mapping.browser_value not in equipment_browser.columns,
    }

    if any(missing.values()):
        raise KeyError(f"Missing columns: {missing}")
    
    lookup = (
        equipment_browser.dropna(subset=["Equipment"])
        .drop_duplicates(subset=["Equipment"]).set_index(
        mapping.browser_key)[mapping.browser_value]
    )

    df[mapping.df_target] = df[mapping.df_key].map(lookup)

    return df


def columns_to_numeric(
        df: pd.DataFrame,
        columns: str | list[str]
    ) -> pd.DataFrame:
    """Convert columns to numeric and round to 2 decimals."""

    df = df.copy()
    
    if isinstance(columns, str):
        df[columns] = pd.to_numeric(
            df[columns], errors='coerce'
        ).round(2)
    else:
        for col in columns:
            df[col] = pd.to_numeric(
                df[col], errors='coerce'
            ).round(2)
    return df


def assign_site(
        df: pd.DataFrame,
        equipment_browser: pd.DataFrame,
        site : dict
    ) -> pd.DataFrame:
    """Assign 'Site' column from equipment_browser (assumes single site)."""

    df = df.copy()
    equipment_browser = equipment_browser.copy()

    target, value = next(iter(site.items()))

    sites = equipment_browser[value].dropna().unique()

    if len(sites) != 1:
        raise ValueError("equipment_browser must contain exactly one unique site name")

    df[target] = sites[0]
    return df


def assign_year_month(
        df: pd.DataFrame,
        year_month: dict
    ) -> pd.DataFrame:
    """Assign 'YearMonth' column as pandas Period[M]."""

    df = df.copy()

    target, value = next(iter(year_month.items()))

    # if len(value) != 1:
    #     raise ValueError("Expected exactly one element YearMonth mapping")

    df[target] = pd.Period(value, freq='M')
    
    return df


def convert_to_datetime(df, columns):
    """
    Convert one or multiple dataframe columns to datetime format 'yyyy-mm-dd hh:mm'.
    If conversion fails for all strategies, the original column is kept unchanged.

    Parameters
    ----------
    df : pandas.DataFrame
    columns : str or list[str]

    Returns
    -------
    pandas.DataFrame
    """

    # if isinstance(columns, str):
    #     columns = [columns]

    df = df.copy()

    for col in columns:

        if col not in df.columns:
            print(f"⚠️ Column '{col}' not found in dataframe.")
            continue

        original_series = df[col]

        conversion_success = False

        # 1️⃣ Try pandas automatic parsing
        try:
            converted = pd.to_datetime(original_series, format= 'mixed')
            conversion_success = True
        except Exception:
            pass

        # 2️⃣ Try common datetime formats
        if not conversion_success:

            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%d/%m/%Y %H:%M",
                "%m/%d/%Y %H:%M",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y"
            ]

            for fmt in formats:
                try:
                    converted = pd.to_datetime(original_series, format=fmt, errors="raise")
                    conversion_success = True
                    break
                except Exception:
                    continue

        # 3️⃣ Try numeric timestamp
        if not conversion_success:
            try:
                converted = pd.to_datetime(original_series, unit="s", errors="raise")
                conversion_success = True
            except Exception:
                pass

        # 4️⃣ Apply formatting if success
        if conversion_success:
            df[col] = converted.dt.strftime("%Y-%m-%d %H:%M")

        else:
            print(f"❌ Unable to convert column '{col}'. Original type preserved.")

    return df


def format_yearmonth_column(df, column="YearMonth"):
    """
    Convert a column to datetime and format it properly.
    - If format is yyyy-mm-dd -> keep full date
    - If format is yyyy-mm -> append -01 as day
    """

    df = df.copy()

    series = df[column].astype(str)
    
    try:
        dt_series = pd.to_datetime(series, errors='coerce')
    except Exception:
        # print(f"❌ Impossible to conert column '{column}' in datetime.")
        return df

    if dt_series.isna().all():
        # print(f"⚠️ column '{column}' couldn't be converted.")
        return df

    def format_func(x):
        if pd.isna(x):
            return x
        
        if x.day == 1 and series.str.len().max() <= 7:
            return x.strftime("%Y-%m")
        else:
            return x.strftime("%Y-%m-%d")

    df[column] = dt_series.apply(format_func)
    return df