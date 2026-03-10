# coding:utf-8

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from backend.fetch_data import fetch_data, DatasetType
from backend.packages.filtering import *
from backend.errors_handling import errors_handling
from frontend.clean_state import init_state



# ============== PAGE CONFIG ==========================
st.set_page_config(page_title= "Operating Hours",)
st.title("Operating Data Processing")


# --------- Create file --------------
@st.cache_data
def convert_csv(df):
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


# =====================================================
# VARIABLES ASSIGNING
# =====================================================
required_keys = [
    "equipment", "smu_hours_dialog",
    "yearmonth_mode_op_hrs_dialog"
]

# ======= Check for required keys existence ===========
for key in required_keys:
    if key not in st.session_state:
        st.warning(
            "Required keys missing values in module <operating_processing.py>."
        )
        st.rerun()

# ======== Keys recovery as constant variable =========
relevant_columns = {
    "Equipment": st.session_state.get("equipment"),
    "SMU Hours": st.session_state.get("smu_hours_dialog")
}

mode = st.session_state.get("yearmonth_mode_op_hrs_dialog")

if mode == "Select a column":
    relevant_columns["YearMonth"] = st.session_state.get(
        "year_month_column_op_hrs_dialog"
    )
    year_month_mapping = None

else:
    year_month_mapping = {
        "YearMonth": st.session_state.get("year_month_value_op_hrs_dialog")
    }

browser_path = st.session_state.get('browser_path_model')
if browser_path is None:
    st.warning("⚠️ No file selected.")
    st.stop()

template_path = st.session_state.get("template_path_model")

equip_column = {"Equipment": "Equipment"}
site = {"Site": "Minesite"}

model_mapping = BrowserMapping(
    df_key= "Equipment",
    df_target= "Model",
    browser_key= "Equipment",
    browser_value= "Model"
)

# ============= Errors constants ====================
duplicated_col = {
    "subset": ["Equipment", "YearMonth"]
}
nan_columns = {"subset": ["Equipment", "SMU Hours"]}
outliers_col = {'column': "SMU Hours", "low": 0.1, "high": 730}

 
# ===================================================
# FUNCTION EXECUTION
# ===================================================
if "df_model" in st.session_state:
    if "df_process" not in st.session_state:
        base_df = st.session_state.get("df_model")
        
        processed_df = fetch_data(
            dataset_type= DatasetType.OPERATING,
            dataset= base_df,
            template_path= template_path,
            browser_path= browser_path,
            selected_columns= relevant_columns,
            equip_column= equip_column,
            site= site,
            year_month= year_month_mapping,
            mapping= model_mapping,
            numeric_columns= "SMU Hours"
        )
        st.session_state.df_process = processed_df

        if st.session_state.get("minesite") == "Essakane":

            if "equip_mapping" not in st.session_state:
                st.session_state.equip_mapping = (
                    st.session_state.df_browser_model
                    .dropna(subset=["Equipment"])
                    .drop_duplicates(subset=["Equipment"])
                    .set_index("Equipment")["Equip Label"]
                    .to_dict()
                )

                st.session_state.df_process["Equipment"] = (
                    st.session_state.df_process["Equipment"]
                    .map(st.session_state.equip_mapping)
                    .fillna(st.session_state.df_process["Equipment"])
                )
        
        unit_key = "time_unit_op_hrs_dialog"
        unit = st.session_state.get(unit_key)

        if unit == 'Min':
            st.session_state.df_process["SMU Hours"] =\
                st.session_state.df_process["SMU Hours"] / 60
        
        elif unit == 'Sec':
            st.session_state.df_process["SMU Hours"] =\
                st.session_state.df_process["SMU Hours"] / 3600
            
    st.session_state.df_process = format_yearmonth_column(
        st.session_state.df_process)
    
    st.dataframe(st.session_state.df_process)
    
    df_process, errors_df =  errors_handling(
        st.session_state.df_process,
        duplicated_col,
        nan_columns,
        outliers_col
    )
       
    # =========== Initialize state to navigate ======
    if "error_step" not in st.session_state:
        st.session_state.error_step = 0
 
    if "error_keys" not in st.session_state:

        order = ['missing_values', 'outliers', 'duplicates']
        st.session_state.error_keys = [e for e in order if e in list(errors_df.keys())]

    if "current_error_index" not in st.session_state:
        st.session_state.current_error_index = 0
    
    # =========== Errors dialog entry ===============
    def show_errors_dialog(): 
            
        st.warning("⚠️ Summary of errors rows in the dataset. Pay attention to handle.")
        summary = pd.DataFrame({
            "Error type": st.session_state.error_keys,
            "Rows count": [len(errors_df[k]) for k in st.session_state.error_keys]
        })
        st.dataframe(summary)

        if summary['Rows count'].sum() == 0:
            st.success("✅ Your dataset haven't got errors rows.")
            if st.button("Close"):
                st.session_state.error_step = 0
                st.session_state.df_download = True
                st.rerun()

        else:
            st.error("🚨 There are few rows that hold errors.")

            if st.button("Next"):
                # --- Move to the first errors type no empty ---
                for i, k in enumerate(st.session_state.error_keys):
                    if not errors_df[k].empty:
                        st.session_state.current_error_index = i
                        st.session_state.error_step = k
                        st.rerun()

    # ====== Dialog managing each error available ======
    def show_errors(): 

        # ----- Errors handling step by step -----
        key = st.session_state.error_step
        st.warning(f"⚠️ Rows with {key.replace('_', ' ')} found in the dataset.")

        # ---------------- AGGRID --------------------
        gb = GridOptionsBuilder.from_dataframe(errors_df[key])
        gb.configure_default_column(
            editable=True,
            filter=True,
            sortable=True
        )
        gb.configure_selection("multiple", use_checkbox= True)

        grid_options = gb.build()

        grid_response = AgGrid(
            errors_df[key],
            gridOptions= grid_options,
            update_mode= GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load= True,
            theme= "streamlit"
        )

        selected_rows = grid_response.get("selected_rows", [])
        edited_df_errors = pd.DataFrame(selected_rows) 
        
        # ----- Buton Next or Confirm if the last --------------
        next_index = st.session_state.current_error_index + 1
        
        while next_index < len(st.session_state.error_keys) and errors_df[
            st.session_state.error_keys[next_index]].empty:

            next_index += 1

        if next_index < len(st.session_state.error_keys):
            if st.button("Next"):
                st.session_state.df_process = pd.concat(
                        [df_process, edited_df_errors], ignore_index= True)
                                
                st.session_state.current_error_index = next_index
                st.session_state.error_step = st.session_state.error_keys[next_index]
                st.rerun()

        else:
            if st.button("Confirm"):
                st.session_state.df_process = pd.concat(
                        [df_process, edited_df_errors], ignore_index= True)
                    
                st.session_state.df_download = True
                st.session_state.error_step = 0
                st.rerun()

    col11, col12 = st.columns([9, 1])        
    with col12:
        # ------ Prime button to accede dialog widget ---------
        if st.button("Errors"):
            st.session_state.error_step = "summary"
        
    if st.session_state.error_step == "summary":
        st.markdown(("Deep view on rows that held errors..."))
        show_errors_dialog()
    
    if st.session_state.error_step in st.session_state.error_keys:
        st.markdown("Handling errors")
        show_errors()

# ===========================================
# DOWNLOAD FILE SESSION
# ===========================================
    with col11:

        if 'df_download' not in st.session_state:
                st.session_state.df_download = False

    if st.session_state.df_download == True:   

        file_name = st.text_input(
            "File Name", width= 200,
            placeholder= 'Enter file name')
 
        # --------- Create file --------------
        csv = st.session_state.df_process.to_csv(index=False, sep=";").encode("utf-8-sig")

        # Downloading button
        if file_name != "":
            st.download_button(
                label="⬇️ Download",
                data=csv,
                file_name=f"{file_name}.csv",
                mime="text/csv"
            )
            
            
# ===============================
# Go back to welcome page
# ===============================      
if st.button("⬅️ Back"):
    keys_to_clear = [
        "df_process",
        "error_step",
        "error_keys",
        "current_error_index",
        "df_download"
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    init_state()
    st.switch_page("model.py") 