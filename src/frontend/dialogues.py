#coding:utf-8
import pandas as pd
import streamlit as st

from backend.packages.kips import check_kpis_value


@st.dialog("📝 Required informations")
def show_modal_operating():

    if "df_model" in st.session_state:
        df_dialog = st.session_state.get("df_model")
    else:
        st.warning("No data found.")
        st.stop()

    st.write("You have to put down these information and submit.")
    
    smu_hours = st.selectbox("Select <SMU Hours> column", df_dialog.columns)
    
    # YearMonth choosing
    year_month = None
    year_month_value = None

    mode = st.radio(
        "How do you want to assign YearMonth ?",
        ["Select a column", "Enter manually a value"]
    )

    if mode == "Select a column":
        year_month = st.selectbox(
            "Select <YearMonth> column",
            df_dialog.columns,
            index= None,
            placeholder= "Select a column"
        )

    else:
        year_month_value = st.text_input(
            "Enter <YearMonth> value (ex: 2026-01)"
        )

    # ============= Check for Downtime Hours Unit ==========
    duration_unit = st.radio(
        "What is the time unit?",
        ['Hrs', 'Min', 'Sec'],
        horizontal= True
    )    

    # ===============================
    # NEXT BUTTON
    # ===============================
    if st.button("NEXT"):

        if not smu_hours:
            st.warning("Please select SMU Hours corresponding column.")
            st.stop()

        if mode == "Select a column" and not year_month:
            st.warning("Please select YearMonth corresponding column.")
            st.stop()

        if mode == "Enter manually a value" and not year_month_value:
            st.warning("Please enter YearMonth value.")
            st.stop()

        # 🔥 GLOBAL STORAGE
        st.session_state.smu_hours_dialog = smu_hours
        st.session_state.year_month_column_op_hrs_dialog = year_month
        st.session_state.year_month_value_op_hrs_dialog = year_month_value
        st.session_state.yearmonth_mode_op_hrs_dialog = mode
        st.session_state.time_unit_op_hrs_dialog = duration_unit

        st.switch_page("pages/operating_processing.py")

        
@st.dialog("📝 Required Informations")
def show_modal_downtime():

    if "df_model" in st.session_state:
        df_process = st.session_state.get('df_model')
    else:
        st.warning("No data found.")
        st.stop()

    st.write("You have to put down these information ands submit.")

    labour_type = st.selectbox("Select <Labour Type> column", df_process.columns, index=None)
    
    work_type = st.selectbox("Select <WorkType> column", df_process.columns, index=None)
    
    comments = st.selectbox("Select <Comments> column", df_process.columns, index=None)
    
    start_hours = st.selectbox("Select <Start Hours> column", df_process.columns, index=None)
    
    end_hours = st.selectbox("Select <End Hours> column", df_process.columns, index=None)
    
    downtime_hours = st.selectbox("Select <Downtime Hours> column", df_process.columns, index=None)    
    
    # ============== YearMonth choosing ==================
    year_month = None
    year_month_value = None

    mode = st.radio(
        "How do you want to assign YearMonth ?",
        ["Select a column", "Enter manually a value"]
    )

    if mode == "Select a column":
        year_month = st.selectbox(
            "Select <YearMonth> column",
            df_process.columns,
            index=None,
            placeholder="Select a column"
        )

    else:
        year_month_value = st.text_input(
            "Enter <YearMonth> value (ex: 2026-01)"
        )

    # ============= Check for Downtime Hours Unit ==========
    duration_unit = st.radio(
        "What is the time unit?",
        ['Hrs', 'Min', 'Sec'],
        horizontal= True
    )

    # ===============================
    # BOUTON NEXT
    # ===============================
    if st.button("NEXT"):

        if not labour_type:
            st.warning("Please select the corresponding labour-type column.")
            st.stop()

        if not work_type:
            st.warning("Please select the corresponding work-type column.")
            st.stop()
        
        if not comments:
            st.warning("Please select the corresponding comments column.")
            st.stop()

        if not start_hours:
            st.warning("Please select the corresponding start-hours column.")
            st.stop()

        if not end_hours:
            st.warning("Please select the corresponding end-hours column.")
            st.stop()

        if not downtime_hours:
            st.warning("Please select the corresponding downtime duration column.")
            st.stop()
        
        if mode == "Select a column" and not year_month:
            st.warning("Please select YearMonth corresponding column.")
            st.stop()

        if mode == "Enter manuelly a value" and not year_month_value:
            st.warning("Please enter YearMonth value.")
            st.stop()

        # 🔥 STOCKAGE GLOBAL
        st.session_state.labour_type_dialog = labour_type
        st.session_state.work_type_dialog = work_type
        st.session_state.comments_dialog = comments
        st.session_state.start_hours_dialog = start_hours
        st.session_state.year_month_column_dt_hrs_dialog = year_month
        st.session_state.end_hours_dialog = end_hours
        st.session_state.downtime_hours_dialog = downtime_hours
        st.session_state.year_month_value_dt_hrs_dialog = year_month_value
        st.session_state.yearmonth_mode_dt_hrs_dialog = mode
        st.session_state.time_unit_dt_hrs_dialog = duration_unit

        st.switch_page("pages/downtime_processing.py")


@st.dialog("✅ Load Operating & Downtime dataset")    
def file_loading_modal():

    uploaded_files = st.file_uploader(
        "Load the Operating and Downtime CSV files",
        type=["csv"],
        accept_multiple_files=True,
        width=600
    )

    if uploaded_files:
        # Reset previous data
        st.session_state["df_down"] = None
        st.session_state["df_op"] = None
        st.session_state["df_down_name"] = None
        st.session_state["df_op_name"] = None

        if len(uploaded_files) != 2:
            st.warning("Please select exactly 2 CSV files.")
            st.stop()
            
        for uploaded_file in uploaded_files:
            df = pd.read_csv(uploaded_file, sep=";")

            if "Equip No" in df.columns:

                if st.session_state["df_down"] is not None:
                    st.warning(
                        f"'{uploaded_file.name}' is another Downtime file. "
                        "Please load one Operating file and one Downtime file."
                    )
                    st.stop()

                st.session_state["df_down"] = df
                st.session_state["df_down_name"] = uploaded_file.name

            elif "Equipment" in df.columns:

                if st.session_state["df_op"] is not None:
                    st.warning(
                        f"'{uploaded_file.name}' is another Operating file. "
                        "Please load one Operating file and one Downtime file."
                    )
                    st.stop()

                st.session_state["df_op"] = df
                st.session_state["df_op_name"] = uploaded_file.name

            else:
                st.warning(
                    f"'{uploaded_file.name}' is not a valid Operating or Downtime file."
                )
                st.stop()

        st.success("✅ Operating and Downtime files successfully loaded.")

        st.write(f"**Operating:** {st.session_state['df_op_name']}")
        st.write(f"**Downtime:** {st.session_state['df_down_name']}")

    # ===============================
    # NEXT
    # ===============================
    if st.button("NEXT", type="primary"):

        if (
            st.session_state.get("df_down") is None
            or st.session_state.get("df_op") is None
        ):
            st.warning("Please load one Operating file and one Downtime file.")
            st.stop()

        df_merge = check_kpis_value(
            df_down=st.session_state.df_down,
            df_op=st.session_state.df_op,
        )

        problem = df_merge[
            df_merge["Used Hrs"] > df_merge["Calendar Hrs"]
        ]

        if problem.empty:
            st.switch_page("pages/clean_view.py")
        else:
            st.switch_page("pages/visualization.py")