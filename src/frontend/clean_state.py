# coding:utf-8

import streamlit as st

def init_state():
    default_states = {
        # "df_model",
        "df_browser_model",
        # "success_message_model",
        "file_name",
        # "excel_file",
        # "sheets",
        # "selected_sheet",
        "minesite_model",
        "equipment_model",
        "df_missed",
        "choice",
        "df_browser_model",
        "browser_path_model",
        "template_path_model",
        "trainer_path_model",
        # Operatibg ,
        "smu_hours_dialog",
        "year_month_column_op_hrs_dialog",
        "year_month_value_op_hrs_dialog",
        "yearmonth_mode_op_hrs_dialog",
        "time_unit_op_hrs_dialog",
        # Downtime dialoge,
        "labour_type_dialog",
        "work_type_dialog",
        "comments_dialog",
        "start_hours_dialog",
        "year_month_column_dt_hrs_dialog",
        "end_hours_dialog",
        "downtime_hours_dialog",
        "year_month_value_dt_hrs_dialog",
        "yearmonth_mode_dt_hrs_dialog",
        "time_unit_dt_hrs_dialog",
        "df_process",
        "df_edited",
        "equipment",
        "minesite",
        "equip_mapping",
        "error_step",
        "error_keys",
        "current_error_index",
        "df_download",
        ""

    }

    for key in default_states:
        if key in st.session_state:
            del st.session_state[key]
