# coding:utf-8
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

from backend.fetch_data import fetch_data, DatasetType
from backend.packages.filtering import format_yearmonth_column, BrowserMapping
from backend.errors_handling import errors_handling
from backend.predict.predictor import fill_description_cat
from frontend.clean_state import init_state

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Downtime Hours")
st.title("Downtime Data Processing")

ERROR_ORDER = [
    'missing_values', 'start_hours_mismatch', 'Negative_Hours',
    'Downtime_imbricated_period', 'downtime_mismatch', 'duplicates'
]

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
    equipment = st.session_state.get('equipment')

    if equipment and equipment in df.columns:
        df[equipment] = df[equipment].map(mapping).fillna(df[equipment])
    return df


def normalize_units(df: pd.DataFrame) -> pd.DataFrame:
    unit = st.session_state.get("time_unit_dt_hrs_dialog")
    df = df.copy()
    
    if unit == "Min":
        df["DowntimeHours"] /= 60
    elif unit == "Sec":
        df["DowntimeHours"] /= 3600
    return df


def prepare_columns():

    mode = st.session_state.get("yearmonth_mode_dt_hrs_dialog")

    relevant_columns = {
        "Equip No": st.session_state.get("equipment"),
        "Labour Type": st.session_state.get("labour_type_dialog"),
        "WorkType": st.session_state.get("work_type_dialog"),
        "Comments": st.session_state.get("comments_dialog"),
        "Start Hours": st.session_state.get("start_hours_dialog"),
        "End Hours": st.session_state.get("end_hours_dialog"),
        "DowntimeHours": st.session_state.get("downtime_hours_dialog")
    }

    if mode == "Select a column":
        relevant_columns["YearMonth"] = st.session_state.get(
            "year_month_column_dt_hrs_dialog")
        year_month = None
    else:
        year_month = {
            "YearMonth": st.session_state.get(
                "year_month_value_dt_hrs_dialog")
        }

    return relevant_columns, year_month


def to_string_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all columns to string for safe UI editing."""
    return df.astype(str)


def restore_types(df: pd.DataFrame) -> pd.DataFrame:
    """Restore proper types after user editing (safe)."""
    df = df.copy()
    for col in ["Start Hours", "End Hours", "DowntimeHours"]:
        if col not in df.columns:
            continue
        if col in ["Start Hours", "End Hours"]:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ======= Check for required keys existence ================= 
check_required_keys([
    "labour_type_dialog", "work_type_dialog", "comments_dialog", "equipment",
    "start_hours_dialog", "end_hours_dialog", "yearmonth_mode_dt_hrs_dialog",
    "downtime_hours_dialog", "year_month_column_dt_hrs_dialog", "df_browser_model",
    "template_path_model"
])

df_browser = get_browser_df()
template_path = st.session_state.get("template_path_model")

# =====================================================
# PROCESSING
# =====================================================
if "df_model" in st.session_state:
    if "df_process" not in st.session_state:

        relevant_columns, year_month_mapping = prepare_columns()
        base_df = st.session_state.get("df_model")

        if "equip_mapping" not in st.session_state:
            st.session_state.equip_mapping = build_equipment_mapping(df_browser)

        base_df = apply_equipment_mapping(base_df, st.session_state.equip_mapping)

        processed_df = fetch_data(
            dataset_type=DatasetType.DOWNTIME,
            dataset=base_df,
            template_path=template_path,
            df_browser=df_browser,
            selected_columns=relevant_columns,
            equip_column={"Equip No": "Equipment"},
            site={"Minesite": "Minesite"},
            year_month=year_month_mapping,
            mapping=BrowserMapping(
                df_key="Equip No",
                df_target="Model",
                browser_key="Equipment",
                browser_value="Model"
            ),
            numeric_columns="DowntimeHours",
            downtime=True
        )

        processed_df = normalize_units(processed_df)
        st.session_state.df_process = processed_df

    # ---- formatting datetime ----
    st.session_state.df_process = format_yearmonth_column(
        st.session_state.df_process)
    
    st.session_state.df_process["Start Hours"] = pd.to_datetime(
        st.session_state.df_process["Start Hours"], errors="coerce"
    ).dt.strftime("%Y-%m-%d %H:%M")

    st.session_state.df_process["End Hours"] = pd.to_datetime(
        st.session_state.df_process["End Hours"], errors="coerce"
    ).dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(st.session_state.df_process)

# =====================================================
# ERRORS HANDLING
# =====================================================
    if "errors_df" not in st.session_state:
        df_process, errors_df = errors_handling(
            st.session_state.df_process,
            {"subset": [
                "YearMonth", "Equip No", "Labour Type",
                "WorkType", "Comments", "Start Hours"
            ]},
            {"subset": [
                "Equip No", "Labour Type", "WorkType",
                "Start Hours", "End Hours", "DowntimeHours"
            ]},
            outlier_columns=None,
            downtime=True
        )
        st.session_state.df_valid = df_process
        st.session_state.errors_df = errors_df

    st.session_state.setdefault("error_keys", [k for k in ERROR_ORDER if k in st.session_state.errors_df])
    st.session_state.setdefault("current_error_index", 0)
    st.session_state.setdefault("error_step", 0)
    st.session_state.setdefault("df_edited", False)

    # ------- Flag for errors handling ----------
    if st.session_state.get("recompute_errors", True):
        df_process, errors_df = errors_handling(
            st.session_state.df_process,
            {"subset": [
                "YearMonth", "Equip No", "Labour Type",
                "WorkType", "Comments", "Start Hours"
            ]},
            {"subset": [
                "Equip No", "Labour Type", "WorkType",
                "Start Hours", "End Hours", "DowntimeHours"
            ]},
            outlier_columns=None,
            downtime=True
        )
        st.session_state.df_valid = df_process
        st.session_state.errors_df = errors_df
        st.session_state.recompute_errors = False


# =====================================================
# WORKTYPE RENAME DIALOG
# =====================================================
@st.dialog("Rename values in <<WorkType>>")
def work_type_dialog():

    df = st.session_state.df_process.copy()

    column1 = ['Labour Type', 'WorkType', 'Comments']
    df[column1] = df[column1].apply(
        lambda col: col.str.replace(r"[\r\n]", "", regex=True)
    )

    column = "WorkType"
    unique_values = df[column].fillna("(vide)").unique()
    mapping = {}

    for val in unique_values:
        new_val = st.text_input(f"{val}", value=val, key=f"rename <<{column}>> --> {val}")
        mapping[val] = new_val

    if st.button("Apply renaming"):
        df[column] = df[column].map(mapping).fillna(df[column])
        st.session_state.df_process = df
        st.session_state.df_edited = True
        st.success("✅ Values renamed successfully")
        st.rerun()

# =====================================================
# UI FUNCTIONS
# =====================================================
def show_summary():

    st.warning(
        "⚠️ Summary of errors rows in the dataset. Pay attention to handle.")
    summary = pd.DataFrame({
        "Error type": st.session_state.error_keys,
        "Rows count": [len(st.session_state.errors_df[k]) for k in st.session_state.error_keys]
    })
    st.dataframe(summary)

    if summary["Rows count"].eq(0).all():
        st.success("✅ Your dataset haven't got errors rows.")
        if st.button("Close"):
            st.session_state.df_process =\
                fill_description_cat(st.session_state.df_process)
            st.session_state.error_step = 0
            st.rerun()
    else:
        st.error("🚨 There are few rows that hold errors.")
        if st.button("Next"):
            # --- Move to the first errors type no empty ---
            for i, k in enumerate(st.session_state.error_keys):
                if not st.session_state.errors_df[k].empty:
                    st.session_state.current_error_index = i
                    st.session_state.error_step = st.session_state.error_keys[i]
                    st.rerun()

def show_error_detail():

    # ---- Errors handling step by step -----
    key = st.session_state.error_step
    st.warning(
        f"⚠️ Rows with {key.replace('_', ' ')} errors found in the dataset.")

    # -------------------- AGGRID ---------------------
    grid_df = st.session_state.errors_df[key].copy()
    for col in ["Start Hours", "End Hours"]:
        if col in grid_df.columns:
            grid_df[col] = pd.to_datetime(
                grid_df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
            grid_df[col] = grid_df[col].fillna("")
    grid_df["YearMonth"] = grid_df["YearMonth"].astype(str)

    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(editable=True, filter=True, sortable=True)
    for col in ["Start Hours", "End Hours"]:
        gb.configure_column(
            col, editable=True, cellEditor="agTextCellEditor", type=["text"])
    gb.configure_selection("multiple", use_checkbox=True)

    grid = AgGrid(
        grid_df,
        gridOptions=gb.build(),
        update_on="SELECTION_CHANGED",
        fit_columns_on_grid_load=True,
        theme="streamlit",
        key=f"errors_grid_{key}"
    )

    selected_rows = grid.get("selected_rows", [])
    selected = pd.DataFrame(selected_rows) if selected_rows else pd.DataFrame()
    
    if not selected.empty:
        selected.columns = selected.columns.astype(str)
        selected = selected.loc[:, ~selected.columns.str.startswith("_")]

        for col in ["Start Hours", "End Hours"]:
            if col in selected.columns:
                selected[col] = pd.to_datetime(selected[col], errors="coerce")

    # ----------- Buton Next or Confirm if the last -----------
    next_index = st.session_state.current_error_index + 1

    while next_index < len(st.session_state.error_keys) and st.session_state.errors_df[
        st.session_state.error_keys[next_index]].empty:
        next_index += 1

    if next_index < len(st.session_state.error_keys):
        if st.button("Next"):
            st.session_state.df_valid = pd.concat(
                [st.session_state.df_valid, selected], ignore_index=True
            ) if not selected.empty else st.session_state.df_valid
            st.session_state.current_error_index = next_index
            st.session_state.error_step = st.session_state.error_keys[next_index]
            st.rerun()
    else:
        if st.button("Confirm"):
            st.session_state.df_valid = pd.concat(
                [st.session_state.df_valid, selected], ignore_index=True
            ) if not selected.empty else st.session_state.df_valid
            st.session_state.df_process = fill_description_cat(st.session_state.df_valid)
            st.session_state.error_step = 0
            st.session_state.df_edited = True
            st.session_state.recompute_errors = True
            st.rerun()

# =====================================================
# UI FLOW
# =====================================================
col_main, col_side = st.columns([9, 1])

with col_side:
    if st.button("Errors"):
        if "errors_df" in st.session_state:
            
            st.session_state.error_step = "summary"
        else:
            st.warning("No errors data available yet.")

if st.session_state.get("error_step") == "summary":
    st.markdown("Deep view on rows that held errors...")
    show_summary()
elif st.session_state.error_step in st.session_state.error_keys:
    show_error_detail()

with col_main:
    st.session_state.setdefault("df_edited", False)
    if st.button("Rename", help='Use this button to rename *WorkType* column elements'):
        work_type_dialog()

# =====================================================
# DOWNLOAD
# =====================================================
if st.session_state.df_edited:
    file_name = st.text_input(
        "File name", width=200,
        placeholder="Enter file name"
    )
    file_name = file_name.strip().replace(" ", "_")
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
    keys_to_clear = [
        "df_process", "error_step", "error_keys",
        "current_error_index", "df_edited"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            st.session_state.pop(key, None)
    init_state()
    st.switch_page("model.py")