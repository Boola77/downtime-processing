#coding:utf-8

# ===========================================================
# Import packages
# ===========================================================
import streamlit as st

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from backend.fetch_data import fetch_data, DatasetType
from backend.packages.filtering import *
from backend.errors_handling import errors_handling
from backend.predict.predict import *
from frontend.clean_state import init_state



# =================== PAGE CONFIG ===========================
st.set_page_config(page_title= "Downtime Hours",)
st.title("Downtime Data Processing")


# --------- Work Type Imputation -----------------
@st.dialog("Rename values in <<WorkType>>")
def work_type():

    df = st.session_state.df_process.copy()
    column = 'WorkType'

    unique_values = df[column].fillna('(vide)').unique()

    mapping = {}

    for val in unique_values:
        new_val = st.text_input(
            label=f"{val}",
            value=val,
            key=f"rename <<{column}>> --> {val}"
        )
        mapping[val] = new_val

    if st.button("Apply renaming"):
        df[column] = df[column].map(mapping).fillna(df[column])
        st.success("✅ Values renamed successfully")
    
        st.session_state.df_process = df
        
        st.session_state.df_edited = True
        st.rerun()
 
# --------- Create file --------------
@st.cache_data
def convert_csv(df):
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


# ===========================================================
# VARIABLES ASSIGNING
# ===========================================================
required_keys = [
    "labour_type_dialog", "work_type_dialog", "comments_dialog", "equipment",
    "start_hours_dialog", "end_hours_dialog", "yearmonth_mode_dt_hrs_dialog",
    "downtime_hours_dialog", "year_month_column_dt_hrs_dialog", "browser_path_model",
    "template_path_model"
]
 
# ======= Check for required keys existence ================= 
for key in required_keys:
    if key not in st.session_state:
        st.warning("Missing values")
        st.rerun()

relevent_columns ={
    "Equip No": st.session_state.get("equipment"),
    "Labour Type": st.session_state.get("labour_type_dialog"),
    "WorkType": st.session_state.get("work_type_dialog"),
    "Comments": st.session_state.get("comments_dialog"),
    "Start Hours": st.session_state.get("start_hours_dialog"),
    "End Hours": st.session_state.get("end_hours_dialog"),
    "DowntimeHours": st.session_state.get("downtime_hours_dialog")
}

mode = st.session_state.get("yearmonth_mode_dt_hrs_dialog")

if mode == "Select a column":
    relevent_columns['YearMonth'] = st.session_state.get(
        'year_month_column_dt_hrs_dialog'
    )
    year_month_mapping = None

else:
    year_month_mapping = {
        "YearMonth": st.session_state.get("year_month_value_dt_hrs_dialog")
    }

browser_path = st.session_state.get("browser_path_model")
if browser_path is None:
    st.warning("⚠️ No file selected.")
    st.stop()

template_path = st.session_state.get("template_path_model")

equip_column = {"Equip No": "Equipment"}
site = {"Minesite": "Minesite"}

model_mapping = BrowserMapping(
    df_key= "Equip No",
    df_target= "Model",
    browser_key= "Equipment",
    browser_value= "Model"
)

# ============= Errors constants ============================
duplicated_col = {
    "subset": [
        "YearMonth", "Equip No", "Labour Type",
        "WorkType", "Comments", "Start Hours"        
    ]
}
nan_columns = {
    "subset": [
        "Equip No", "Labour Type", "WorkType",
        "Start Hours", "End Hours", "DowntimeHours"
    ]
}


# ===========================================================
# FUNCTION EXECUTION
# ===========================================================
if "df_model" in st.session_state:
    if 'df_process' not in st.session_state:
        base_df = st.session_state.get("df_model")

        processed_df = fetch_data(
            dataset_type= DatasetType.DOWNTIME,
            dataset= base_df,
            template_path= template_path,
            browser_path= browser_path,
            selected_columns= relevent_columns,
            equip_column= equip_column,
            site= site,
            year_month= year_month_mapping,
            mapping= model_mapping,
            numeric_columns= "DowntimeHours",
            downtime= True
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

                st.session_state.df_process["Equip No"] = (
                    st.session_state.df_process["Equip No"]
                    .map(st.session_state.equip_mapping)
                    .fillna(st.session_state.df_process["Equip No"])
                )

        unit_key = "time_unit_dt_hrs_dialog"
        unit = st.session_state.get(unit_key)

        if unit == 'Min':
            st.session_state.df_process["DowntimeHours"] =\
                st.session_state.df_process["DowntimeHours"] / 60
        
        elif unit == 'Sec':
            st.session_state.df_process["DowntimeHours"] =\
                st.session_state.df_process["DowntimeHours"] / 3600

    st.session_state.df_process = format_yearmonth_column(
        st.session_state.df_process)
    
    st.session_state.df_process["Start Hours"] =\
        pd.to_datetime(st.session_state.df_process["Start Hours"], format= 'mixed'
                        ).dt.strftime("%Y-%m-%d %H:%M")
    
    st.session_state.df_process["End Hours"] =\
        pd.to_datetime(st.session_state.df_process["End Hours"], format= 'mixed'
                        ).dt.strftime("%Y-%m-%d %H:%M")
    
    st.dataframe(st.session_state.df_process)
    
    df_process, errors_df = errors_handling(
        st.session_state.df_process,
        duplicated_col,
        nan_columns,
        outlier_columns= None,
        downtime= True
    )
    
    # =========== Initialize state to navigate ==============
    if "error_step" not in st.session_state:
        st.session_state.error_step = 0

    if "error_keys" not in st.session_state:

        order = ["missing_values", "downtime_mismatch", "duplicates"]
        st.session_state.error_keys = [e for e in order if e in list(errors_df.keys())]

    if "current_error_index" not in st.session_state:
        st.session_state.current_error_index = 0
        
    # ============= Errors dialog entry =====================2
    def show_errors_dialog():
        
        st.warning("⚠️ Summary of errors rows in the dataset. Pay attention to handle.")
        summary = pd.DataFrame({
            "Error type": st.session_state.error_keys,
            "Rows count": [len(errors_df[k]) for k in st.session_state.error_keys]
        })
        st.dataframe(summary)

        if summary['Rows count'].sum() == 0:
            st.success("✅ Your dataset haven't got errors rows.")
            if st.button('Close'):
                st.session_state.error_step = 0

                nan_mask = st.session_state.df_process['Description CAT'].isna()
                st.session_state.df_process.loc[nan_mask, 'Description CAT'] = \
                    st.session_state.df_process.loc[nan_mask, :].apply(predict, axis=1)
                
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

        # ---- Errors handling step by step -----
        key = st.session_state.error_step
        st.warning(f"⚠️ Rows with {key.replace('_', ' ')} errors found in the dataset.")
        
        # -------------------- AGGRID ---------------------
        gb = GridOptionsBuilder.from_dataframe(errors_df[key])
        gb.configure_default_column(
            editable= True,
            filter= True,
            sortable= True
        )
        gb.configure_selection("multiple", use_checkbox= True)
   
        grid_options = gb.build()
        
        grid_response = AgGrid(
            errors_df[key],
            gridOptions= grid_options,
            update_on= 'selectionChanged',
            fit_columns_on_grid_load= True,
            theme= "streamlit",
            key=f"errors_grid_{key}"
        )
        
        selected_rows = grid_response.get("selected_rows", [])
        edited_df_errors = pd.DataFrame(selected_rows)     
                               
        # ----------- Buton Next or Confirm if the last -----------
        next_index = st.session_state.current_error_index + 1

        while next_index < len(st.session_state.error_keys) and errors_df[
            st.session_state.error_keys[next_index]].empty:

            next_index += 1

        if next_index < len(st.session_state.error_keys):
            if st.button("Next"):
                st.session_state.df_process = pd.concat(
                    [df_process, edited_df_errors],
                    ignore_index=True
                )

                st.session_state.current_error_index = next_index
                st.session_state.error_step = st.session_state.error_keys[next_index]
                st.rerun()                    
                
        else:
            if st.button("Confirm"):
                st.session_state.df_process = pd.concat(
                    [df_process, edited_df_errors], ignore_index=True)
                
                nan_mask = st.session_state.df_process['Description CAT'].isna()
                st.session_state.df_process.loc[nan_mask, 'Description CAT'] = \
                    st.session_state.df_process.loc[nan_mask, :].apply(predict, axis=1)

                st.session_state.error_step = 0                                   
                st.rerun()

    col11, col12 = st.columns([9, 1])        
    with col12:
        # --------- Prime button to accede dialog widget ---------
        if st.button("Errors"):            
            st.session_state.error_step = "summary"   

    if st.session_state.error_step == "summary":
        st.markdown("Deep view on rows that held errors...")
        show_errors_dialog()

    if st.session_state.error_step in st.session_state.error_keys:
        st.markdown("Handling errors")
        show_errors()  

    # ===========================================
    # DOWNLOAD FILE SESSION
    # ===========================================

    with col11:

        if 'df_edited' not in st.session_state:
                st.session_state.df_edited = False
        
        if st.button("WorkType"):          
            work_type()

    if st.session_state.df_edited == True:        
        
        file_name = st.text_input(
            "File name", width= 200,
            placeholder= "Enter file name")
        file_name = file_name.strip().replace(" ", "_")
        
        csv = convert_csv(st.session_state.df_process)
        
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
        "df_edited"
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
             
    init_state()
    st.switch_page("model.py")