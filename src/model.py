import streamlit as st
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from frontend.read_files import read_csv_file, read_excel_file
from frontend.dialogues import show_modal_downtime, show_modal_operating
from frontend.clean_state import init_state


# ==========================================================
# CONFIG
# ==========================================================
st.set_page_config(layout="wide")
st.title("📊 Data Processing Platform")


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
    'Agbaou', 'Bonikro', 'Essakane', 'Fekola',
    'Goulamina', 'Kouroussa', 'Sangaredi',
    'Seguela', 'Siguiri', 'Simandou',
    'SNIM', 'Tongon'
]


# ==========================================================
# FILE UPLOAD SECTION
# ==========================================================
uploaded_file = st.file_uploader(
    "Load Excel or CSV file",
    type=["xlsx", "csv", "xls", "xlsm"],
    width = 600
)

# if 'df_model' not in st.session_state:
init_state_()


# ================== RUN UPLOADING ============
if uploaded_file and uploaded_file.name != st.session_state.file_name:

    # RESET ENTIRELY AT EACH LOADING
    for key in [
       "df_model", "success_message_model", "file_name", "excel_file",
        "sheets", "selected_sheet", "minesite_model", "equipment_model",
        "df_missed", "df_browser_model"
    ]:
        st.session_state[key] = None
    st.session_state.choice = "Operating"

    init_state()

    file_name = uploaded_file.name.lower()

    # ================= CSV =================
    if file_name.endswith(".csv"):
        df_model = read_csv_file(uploaded_file)
        st.session_state.df_model = df_model.copy()

        st.session_state.success_message_model = "CSV file successfully loaded ✅"
        
        
    # ================= EXCEL =================
    else:
        try:
            excel_file, sheets = read_excel_file(uploaded_file)             
            st.session_state.excel_file = excel_file
            st.session_state.sheets = sheets

            st.session_state.success_message_model = "Excel file successfully loaded ✅"         
                              
        except Exception as e:
            st.error(f"Wrong file extension: {e}")
    
    st.session_state.file_name = uploaded_file.name


# ================= Display Success Message =================
if st.session_state.success_message_model is not None:    
    st.success(st.session_state.success_message_model)


# ==========================================================
# EXCEL SHEET
# ==========================================================
if st.session_state.sheets is not None:                

    left, right = st.columns(2)
    left.header(f"Sheets available = {len(st.session_state.sheets)}")

    selected_sheet = right.selectbox(
        "Choose a sheet",
        st.session_state.sheets,
        key= 'selected_sheet'
    )
    
    
    if selected_sheet:
        df_model = pd.read_excel(
            st.session_state.excel_file,
            sheet_name= selected_sheet
        )
        st.session_state.df_model = df_model.copy()
    

# ==========================================================
# DATA EDITING SECTION
# ==========================================================
if st.session_state.df_model is not None:

    df_model = st.session_state.df_model

    # ================= Mine Site =================
    minesite_model = st.selectbox("Select <site name>", site_list,
                                  key= 'minesite_model', width= 400,
                                  placeholder= 'Select mine site name')

    if minesite_model:

        BASE_DIR = os.getcwd()
        
        browser_path = os.path.join(
            BASE_DIR,
            "data",
            "Equipments",
            f"{minesite_model}.csv"
        )

        if not os.path.exists(browser_path):
            st.error(f"File not found: {browser_path}")
        else:
            df_browser_model = pd.read_csv(browser_path, sep=None, engine='python')

        st.session_state.df_browser_model = df_browser_model

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

        # ================= AGGRID =================
        gb = GridOptionsBuilder.from_dataframe(df_model)
        gb.configure_default_column(
            editable=True,
            filter=True,
            sortable=True
        )
        gb.configure_selection("multiple")

        grid_options = gb.build()

        grid_response = AgGrid(
            df_model,
            gridOptions= grid_options,
            update_mode= GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load= True,
            theme= "streamlit"
        )
 
        edited_df_model = pd.DataFrame(grid_response["data"])

        # Persist edited dataframe
        st.session_state.df_model = edited_df_model

        # ================= Equipment Column =================
        equipment_model = st.selectbox("Select <Equipment number column>",
                                 edited_df_model.columns, key= 'equipment_model',
                                 width= 500, placeholder= 'Select column that hold equipment identifier number')        
        
        if equipment_model:

            if minesite_model == 'Essakane':
                df_missed = df_browser_model[
                    ~df_browser_model['Equipment'].isin(
                        edited_df_model[equipment_model].unique())][[
                            'Equip Label', 'Model']].reset_index(drop=True)
                if not df_missed.empty:
                    st.session_state.df_missed = df_missed

            else:            
                df_missed = df_browser_model[
                    ~df_browser_model['Equipment'].isin(
                        edited_df_model[equipment_model].unique())][[
                            'Equipment', 'Model']].reset_index(drop=True)
                if not df_missed.empty:
                    st.session_state.df_missed = df_missed            
            
            # 🔹 Show if only df_missed existes
            if st.session_state.df_missed is not None:
                st.warning("⚠️ List of equipments not found in browser mapping")
                st.dataframe(st.session_state.df_missed)
            else:
                st.success('✅ All equipments are include data.')

            # ==================================================
            # PROCESSING SECTION
            # ==================================================
            st.subheader("✒️ PROCESS DATA")

            choice = st.radio(
                "Choose processing type:",
                ["Operating", "Downtime"],
                horizontal=True,
                key= 'choice'
            )
            
            if st.button("➡️ Run"):

                st.session_state.equipment = equipment_model
                st.session_state.minesite = minesite_model
                  
                              

                if st.session_state.choice == "Operating":
                    show_modal_operating()
                else:
                    show_modal_downtime()