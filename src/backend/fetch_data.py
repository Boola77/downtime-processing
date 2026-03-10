# coding:utf-8

from enum import Enum
from typing import Mapping
from backend.packages.filtering import *


class DatasetType(str, Enum):
    OPERATING = "operating"
    DOWNTIME = "downtime"


# ----------------- Orchestrator -----------------
def fetch_data(
        dataset_type: DatasetType,
        dataset: pd.DataFrame,
        template_path: str,
        browser_path: str,
        selected_columns: Mapping[str, str | None] | None,
        equip_column: Mapping[str, str],
        site: Mapping[str, str],
        year_month: Mapping[str, str | None] | None,
        mapping: BrowserMapping,
        numeric_columns: str | list[str] | None = None,
        downtime: bool = False
    ) -> pd.DataFrame:
    """
    Prepare operating or downtime dataset by filtering, cleaning, and adding metadata.
    """

    # --- Read inputs
    df_source = dataset.copy()
    df_browser = pd.read_csv(browser_path)

    # --- Template
    df = create_template(
        template_path,
        template= dataset_type.value
    )

    # --- Pipeline
    if selected_columns:
        df = fill_columns(df, df_source, selected_columns)

    df = filter_existing_equipment(
        df,
        df_browser,
        equip_column
    )

    if downtime:
        df =\
            convert_to_datetime(df, columns=["Start Hours", "End Hours"])
 
    if numeric_columns:
        df = columns_to_numeric(df, numeric_columns)

    df = assign_site(df, df_browser, site)
    
    if year_month:
        df = assign_year_month(df, year_month)
        
    df = assign_model(df, df_browser, mapping)

    return df