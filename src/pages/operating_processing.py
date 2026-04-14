# coding:utf-8
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

from backend.fetch_data import fetch_data, DatasetType
from backend.packages.filtering import format_yearmonth_column, BrowserMapping
from backend.errors_handling import errors_handling
from frontend.clean_state import init_state



# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Operating Hours")
st.title("Operating Data Processing")

ERROR_ORDER = ['missing_values', 'outliers', 'duplicates', 'Negative_Hours']


# =====================================================
# UTILS
# =====================================================
@st.cache_data
def convert_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


def check_required_keys(keys: list):
    missing = [k for k in keys if k not in st.session_state]
    if missing:
        st.warning(f"Missing required keys: {missing}")
        st.stop()


def get_browser_df():
    df = st.session_state.get("df_browser_model")
    if df is None or (hasattr(df, "empty") and df.empty):
        st.warning("⚠️ No file selected.")
        st.stop()
    return df


def build_equipment_mapping(df_browser: pd.DataFrame) -> dict:
    minesite = st.session_state.get("minesite")
    column = "On Site Id" if minesite in ["Essakane", 'Goulamina/CORICA'] else "Equip Label"

    return (
        df_browser
        .dropna(subset=[column])
        .drop_duplicates(subset=[column])
        .set_index(column)["Equipment"]
        .to_dict()
    )


def apply_equipment_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    df = df.copy()
    equipment_col = st.session_state.get("equipment")
    df[equipment_col] = df[equipment_col].map(mapping).fillna(df[equipment_col])
    return df


def normalize_units(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    unit = st.session_state.get("time_unit_op_hrs_dialog")

    if unit == "Min":
        df["SMU Hours"] /= 60
    elif unit == "Sec":
        df["SMU Hours"] /= 3600
    return df


def prepare_columns():
    mode = st.session_state.get("yearmonth_mode_op_hrs_dialog")
    relevant = {
        "Equipment": st.session_state.get("equipment"),
        "SMU Hours": st.session_state.get("smu_hours_dialog")
    }
    if mode == "Select a column":
        relevant["YearMonth"] = st.session_state.get(
            "year_month_column_op_hrs_dialog"
        )
        year_month = None
    else:
        year_month = {
            "YearMonth": st.session_state.get(
                "year_month_value_op_hrs_dialog"
            )
        }
    return relevant, year_month


# =====================================================
# INITIAL CHECKS
# =====================================================
check_required_keys([
    "equipment",
    "smu_hours_dialog",
    "yearmonth_mode_op_hrs_dialog"
])

df_browser = get_browser_df()
template_path = st.session_state.get("template_path_model")



# =====================================================
# DATA PROCESSING
# =====================================================
if "df_model" in st.session_state:

    if "df_process" not in st.session_state:

        relevant_columns, year_month_mapping = prepare_columns()
        base_df = st.session_state.get("df_model").copy()

        # ---- mapping ----
        if "equip_mapping" not in st.session_state:
            st.session_state.equip_mapping =\
                build_equipment_mapping(df_browser)
        base_df =\
            apply_equipment_mapping(base_df, st.session_state.equip_mapping)

        processed_df = fetch_data(
            dataset_type=DatasetType.OPERATING,
            dataset=base_df,
            template_path=template_path,
            df_browser=df_browser,
            selected_columns=relevant_columns,
            equip_column={"Equipment": "Equipment"},
            site={"Site": "Minesite"},
            year_month=year_month_mapping,
            mapping=BrowserMapping(
                df_key="Equipment",
                df_target="Model",
                browser_key="Equipment",
                browser_value="Model"
            ),
            numeric_columns="SMU Hours"
        )

        # ---- units ----
        processed_df = normalize_units(processed_df)
        st.session_state.df_process = processed_df
    
    # ---- formatting ----
    st.session_state.df_process =\
        format_yearmonth_column(st.session_state.df_process)
    st.dataframe(st.session_state.df_process)

# =====================================================
# ERROR HANDLING
# =====================================================
df_process, errors_df = errors_handling(
    st.session_state.df_process,
    {"subset": ["Equipment", "YearMonth"]},
    {"subset": ["Equipment", "SMU Hours"]},
    {"column": "SMU Hours", "low": 0.1, "high": 730}
)

st.session_state.df_valid = df_process

# ---- init state ----
st.session_state.setdefault("error_step", 0)
st.session_state.setdefault("current_error_index", 0)

st.session_state.setdefault(
    "error_keys", [e for e in ERROR_ORDER if e in errors_df])
st.session_state.setdefault("df_download", False)


# =====================================================
# UI FUNCTIONS
# =====================================================
def show_summary():

    st.warning("⚠️ Summary of dataset errors")
    summary = pd.DataFrame({
        "Error type": st.session_state.error_keys,
        "Rows count": [len(errors_df[k]) for k in st.session_state.error_keys]
    })
    st.dataframe(summary)

    if summary["Rows count"].sum() == 0:
        st.success("✅ No error.")
        if st.button("Close"):
            st.session_state.df_download = True
            st.session_state.error_step = 0
            st.rerun()
    else:
        if st.button("Next"):
            for i, k in enumerate(st.session_state.error_keys):
                if not errors_df[k].empty:
                    st.session_state.current_error_index = i
                    st.session_state.error_step = k
                    st.rerun()

def show_error_detail():

    key = st.session_state.error_step
    st.warning(f"⚠️ Handling {key.replace('_', ' ')}")

    grid_df = errors_df[key]
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(editable=True, filter=True, sortable=True)
    gb.configure_selection("multiple", use_checkbox=True)

    grid =\
        AgGrid(grid_df, gridOptions=gb.build(), update_on="SELECTION_CHANGED")
    
    selected_rows = grid.get("selected_rows", [])
    selected =\
        pd.DataFrame(selected_rows).loc[:, ~pd.DataFrame(
            selected_rows
        ).columns.str.startswith("_")] if selected_rows else pd.DataFrame()

    next_index = st.session_state.current_error_index + 1
    while next_index < len(st.session_state.error_keys) and errors_df[st.session_state.error_keys[next_index]].empty:
        next_index += 1

    if next_index < len(st.session_state.error_keys):
        if st.button("Next"):
            st.session_state.df_valid = pd.concat(
                [st.session_state.df_valid, selected],
                ignore_index=True
            ) if not selected.empty else st.session_state.df_valid
            st.session_state.current_error_index = next_index
            st.session_state.error_step = st.session_state.error_keys[next_index]
            st.rerun()
    else:
        if st.button("Confirm"):
            st.session_state.df_valid = pd.concat(
                [st.session_state.df_valid, selected],
                ignore_index=True
            ) if not selected.empty else st.session_state.df_valid
            st.session_state.df_process = st.session_state.df_valid
            st.session_state.df_download = True
            st.session_state.error_step = 0
            st.rerun()


# =====================================================
# UI FLOW
# =====================================================
col_main, col_side = st.columns([9,1])
with col_side:
    if st.button("Errors"):
        st.session_state.error_step = "summary"

if st.session_state.error_step == "summary":
    show_summary()
elif st.session_state.error_step in st.session_state.error_keys:
    show_error_detail()


# =====================================================
# DOWNLOAD
# =====================================================
if st.session_state.df_download:
    file_name = st.text_input(
        "File Name",
        placeholder="Enter file name",
        width= 250
    ).strip().replace(" ", "_")

    if file_name:
        st.download_button(
            label="⬇️ Download",
            data=convert_csv(st.session_state.df_process),
            file_name=f"{file_name}.csv",
            mime="text/csv"
        )

# =====================================================
# NAVIGATION
# =====================================================
if st.button("⬅️ Back"):
    for key in [
        "df_process",
        "error_step",
        "error_keys",
        "current_error_index",
        "df_download"
    ]:
        st.session_state.pop(key, None)
        
    init_state()
    st.switch_page("model.py")