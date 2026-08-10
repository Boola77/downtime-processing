# coding:utf-8
import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder

from frontend.read_files import read_csv_file, read_excel_file
from frontend.dialogues import show_modal_downtime, show_modal_operating, file_loading_modal
from frontend.clean_state import init_state



# ==========================================================
# CONFIG
# ==========================================================
st.set_page_config(layout="wide")
st.title("📊 Data Processing Platform")


def clear_processing_states():
    """
    Reset complet avant le chargement d'un nouveau fichier.
    Supprime tous les états liés à l'ancien traitement.
    """

    keys_to_clear = [

        # ==========================
        # DATA PRINCIPALE
        # ==========================
        "df_model",
        "df_process",
        "df_valid",
        "df_browser_model",
        "df_missed",

        # ==========================
        # FICHIER
        # ==========================
        "file_name",
        "excel_file",
        "sheets",
        "selected_sheet",
        "last_sheet",
        "success_message_model",

        # ==========================
        # CONFIG
        # ==========================
        "minesite_model",
        "equipment_model",
        "minesite",
        "equipment",
        "choice",

        # ==========================
        # PATH
        # ==========================
        "browser_path_model",
        "template_path_model",
        "trainer_path_model",

        # ==========================
        # MAPPING
        # ==========================
        "equip_mapping",
        "last_equipment",

        # ==========================
        # OPERATING
        # ==========================
        "smu_hours_dialog",
        "time_unit_op_hrs_dialog",
        "yearmonth_mode_op_hrs_dialog",
        "year_month_column_op_hrs_dialog",
        "year_month_value_op_hrs_dialog",

        # ==========================
        # DOWNTIME
        # ==========================
        "labour_type_dialog",
        "work_type_dialog",
        "comments_dialog",
        "start_hours_dialog",
        "end_hours_dialog",
        "downtime_hours_dialog",

        "time_unit_dt_hrs_dialog",
        "yearmonth_mode_dt_hrs_dialog",
        "year_month_column_dt_hrs_dialog",
        "year_month_value_dt_hrs_dialog",

        # ==========================
        # ERRORS
        # ==========================
        "errors_df",
        "error_keys",
        "error_step",
        "current_error_index",
        "recompute_errors",

        # ==========================
        # DOWNLOAD
        # ==========================
        "df_download",
        "df_edited",

    ]

    for key in keys_to_clear:
        st.session_state.pop(key, None)
        

def clean_for_streamlit(df):
    df = df.copy()

    for col in df.columns:
        series = df[col]

        # ignore already clean columns
        if pd.api.types.is_datetime64_any_dtype(series):
            continue

        # 1. numeric check
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().mean() > 0.85:
            df[col] = numeric
            continue

        # 2. datetime ONLY if strong signal
        if series.astype(str).str.contains(r"\d{2,4}[-/]\d{1,2}[-/]\d{1,2}", na=False).mean() > 0.7:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            if parsed.notna().mean() > 0.85:
                df[col] = parsed
                continue

        # 3. fallback SAFE
        df[col] = series.astype("string")

    return df


# ==========================================================
# CACHE (PERF ONLY)
# ==========================================================
@st.cache_data
def load_browser(path):
    for enc in ["utf-8", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Impossible de lire le CSV (encoding inconnu)")


# ==========================================================
# SESSION STATE INITIALIZATION
# ==========================================================
def init_state_():
    default_states = {
        "df_model": None,
        "df_browser_model": None,
        "success_message_model": None,
        "file_name": None,
        "excel_file": None,
        "sheets": None,
        "selected_sheet": None,
        "minesite_model": None,
        "equipment_model": None,
        "df_missed": None,
        "choice": "Operating"
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value


site_list = [
    'Agbaou/Mota', 'Bonikro/Mota', 'Essakane', 'Fekola',
    'Goulamina/CORICA', 'Kouroussa', 'Sangaredi/CBG',
    'Seguela', 'Siguiri', 'Simandou/Mota',
    'SNIM-Guelb', 'Tongon', 'SNTP'
]


# KPI's Visualization
col_back, col_dpp = st.columns([9, 1])
with col_dpp:
    if st.button("DPP ➡️"):
        st.session_state["df_down"] = None
        st.session_state["df_op"] = None
        file_loading_modal()

# ==========================================================
# FILE UPLOAD SECTION
# ==========================================================
uploaded_file = st.file_uploader(
    "Load Excel or CSV file",
    type=["xlsx", "csv", "xls", "xlsm"],
    width=600
)

init_state_()


# ================== RUN UPLOADING ==================
if uploaded_file and uploaded_file.name != st.session_state.get("file_name"):

    # nouveau fichier = nettoyage complet
    clear_processing_states()

    init_state_()

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):

        df_model = read_csv_file(uploaded_file)
        df_model = clean_for_streamlit(df_model)

        st.session_state.df_model = df_model
        st.session_state.success_message_model = (
            "CSV file successfully loaded ✅"
        )

    else:
        try:
            excel_file, sheets = read_excel_file(uploaded_file)

            st.session_state.excel_file = excel_file
            st.session_state.sheets = sheets

            st.session_state.success_message_model = (
                "Excel file successfully loaded ✅"
            )

        except Exception as e:
            st.error(f"Wrong file extension: {e}")

    st.session_state.file_name = uploaded_file.name


# ================= Display Success Message =================
if st.session_state.success_message_model is not None:
    st.success(st.session_state.success_message_model)


# ==========================================================
# EXCEL SHEET (OPTIMISÉ)
# ==========================================================
if st.session_state.sheets is not None:

    left, right = st.columns(2)
    left.header(f"Sheets available = {len(st.session_state.sheets)}")

    selected_sheet = right.selectbox(
        "Choose a sheet",
        st.session_state.sheets,
        key='selected_sheet'
    )

    if selected_sheet:
        if "last_sheet" not in st.session_state or st.session_state.last_sheet != selected_sheet:
            st.session_state.last_sheet = selected_sheet

            df_model = pd.read_excel(
                st.session_state.excel_file,
                sheet_name=selected_sheet
            )

            df_model = clean_for_streamlit(df_model)
            st.session_state.df_model = df_model


# ==========================================================
# DATA EDITING SECTION
# ==========================================================
if st.session_state.df_model is not None:

    df_model = st.session_state.df_model

    minesite_model = st.selectbox(
        "Select <site name>", site_list,
        key='minesite_model', width=400,
        placeholder='Select mine site name'
    )

    if minesite_model:

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        browser_path = os.path.join(
            BASE_DIR,
            "data",
            "Equipments",
            "Equipment Browser_v3.csv"
        )

        if not os.path.exists(browser_path):
            st.error(f"File not found: {browser_path}")
        else:
            # ⚡ cached read
            df_browser_model = load_browser(browser_path)

        st.session_state.df_browser_model = df_browser_model[
            df_browser_model.Minesite.fillna('')
            .str.strip()
            .str.lower() == minesite_model.strip().lower()
        ].reset_index(drop=True)

        if "browser_path_model" not in st.session_state:
            st.session_state.browser_path_model = browser_path

        if "template_path_model" not in st.session_state:
            st.session_state.template_path_model = os.path.join(
                BASE_DIR,
                "data",
                "template",
                "Template.xlsx"
            )

        if "trainer_path_model" not in st.session_state:
            st.session_state.trainer_path_model = os.path.join(BASE_DIR, "data", "model")

        st.subheader("🗳️ Editable Table")

        gb = GridOptionsBuilder.from_dataframe(df_model)
        gb.configure_default_column(editable=True, filter=True, sortable=True)
        gb.configure_selection("multiple")

        grid_options = gb.build()

        grid_response = AgGrid(
            df_model,
            gridOptions=grid_options,
            update_on="MODEL_CHANGED",  # inchangé
            fit_columns_on_grid_load=True,
            theme="streamlit"
        )

        edited_df_model = pd.DataFrame(grid_response["data"])
        edited_df_model = clean_for_streamlit(edited_df_model)

        st.session_state.df_model = edited_df_model

        equipment_model = st.selectbox(
            "Select <Equipment number column>",
            edited_df_model.columns,
            key='equipment_model',
            width=500,
            placeholder='Select column that hold equipment identifier number'
        )

        if equipment_model:

            st.session_state.df_browser_model = clean_for_streamlit(st.session_state.df_browser_model)
            edited_df_model = clean_for_streamlit(edited_df_model)

            # ⚡ recalcul seulement si colonne change
            if "last_equipment" not in st.session_state or st.session_state.last_equipment != equipment_model:

                st.session_state.last_equipment = equipment_model

                # if minesite_model in ['Essakane', 'Goulamina/CORICA']:
                df_missed = st.session_state.df_browser_model[
                    ~st.session_state.df_browser_model['On Site Id'].isin(
                        edited_df_model[equipment_model].unique())
                ][['Equipment', 'On Site Id', "SerialNumber", 'Model', "Parent Product Family", "Status"]].reset_index(drop=True)

                df_missed.rename(columns={'On Site Id': equipment_model}, inplace=True)

                # else:
                #     df_missed = st.session_state.df_browser_model[
                #         ~st.session_state.df_browser_model['On Site Id'].isin(
                #             edited_df_model[equipment_model].unique())
                #     ][['Equipment', 'On Site Id', "SerialNumber", 'Model', "Parent Product Family", "Status"]].reset_index(drop=True)

                #     df_missed.rename(columns={'On Site Id': equipment_model}, inplace=True)

                st.session_state.df_missed = df_missed if not df_missed.empty else None

            if st.session_state.df_missed is not None:
                st.warning("⚠️ List of equipments not found in browser mapping")
                st.dataframe(st.session_state.df_missed)
            else:
                st.success('✅ All equipments are include data.')

            st.subheader("✒️ PROCESS DATA")

            choice = st.radio(
                "Choose processing type:",
                ["Operating", "Downtime"],
                horizontal=True,
                key='choice'
            )

            if st.button("➡️ Run"):

                st.session_state.equipment = equipment_model
                st.session_state.minesite = minesite_model

                if st.session_state.choice == "Operating":
                    show_modal_operating()
                else:
                    show_modal_downtime()