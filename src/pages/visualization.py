import io
import zipfile

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

from backend.packages.kips import check_kpis_value


# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="DPP Request")
st.title("Calendar Hours vs Used Hours")


# =====================================================
# FUNCTIONS
# =====================================================
def convert_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


def create_zip(
    df_down: pd.DataFrame,
    df_op: pd.DataFrame,
    down_name: str,
    op_name: str,
) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(down_name, convert_csv(df_down))
        zf.writestr(op_name, convert_csv(df_op))
    buffer.seek(0)
    return buffer


def build_grid(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """
    Editable AgGrid that returns cleaned edited DataFrame (like show_error_detail UX)
    """    

    # -------------------- AGGRID ---------------------
    df = df.reset_index(drop=True).copy()
    for col in ["Start Hours", "End Hours"]:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
            df[col] = df[col].fillna("")
    df["YearMonth"] = df["YearMonth"].astype(str)

    gb = GridOptionsBuilder.from_dataframe(df)
    for col in ["Start Hours", "End Hours"]:
        gb.configure_column(
            col, editable=True, cellEditor="agTextCellEditor", type=["text"])
    gb.configure_default_column(
        editable=True,
        filter=True,
        sortable=True
    )
    gb.configure_selection(
        selection_mode="multiple",
        use_checkbox=True
    )
    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.MODEL_CHANGED
        | GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        key=key
    )

    # edited_df = pd.DataFrame(grid['data'])

    # selected = pd.DataFrame(grid["selected_rows"])

    # ================================
    # GET DATA (EDITED TABLE)
    # ================================
    selected_rows = grid.selected_rows
    selected = pd.DataFrame(selected_rows)# if selected_rows else pd.DataFrame()

    if not selected.empty:
        selected.columns = selected.columns.astype(str)
        selected = selected.loc[:, ~selected.columns.str.startswith("_")]

        for col in ["Start Hours", "End Hours"]:
            if col in selected.columns:
                selected[col] = pd.to_datetime(selected[col], errors="coerce")
    
    # return pd.concat([selected, edited_df], ignore_index=True)
    return selected


# =====================================================
# LOAD DATA
# =====================================================
df_down = st.session_state.get("df_down")
df_op = st.session_state.get("df_op")
down_name = st.session_state.get("df_down_name", "down.csv")
op_name = st.session_state.get("df_op_name", "op.csv")

if df_down is None or df_op is None:
    st.error("Dataframe missing")
    st.stop()

# Init process only once
if "df_down_process" not in st.session_state:
    st.session_state.df_down_process = df_down.copy()
if "df_op_process" not in st.session_state:
    st.session_state.df_op_process = df_op.copy()

if "edited_down" not in st.session_state:
        st.session_state.edited_down = pd.DataFrame()

# =====================================================
# CHECK PROBLEMS
# =====================================================
df_merge = check_kpis_value(
    df_down=st.session_state.df_down_process.copy(),
    df_op=st.session_state.df_op_process.copy()
)

required = {
    "Equipment",
    "Used Hrs",
    "Calendar Hrs"
}
missing = required - set(df_merge.columns)
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

problem = df_merge[
    df_merge["Used Hrs"] > df_merge["Calendar Hrs"]
]

col_back, col_zip = st.columns([8, 2])
# =====================================================
# NO MORE ERRORS
# =====================================================
if problem.empty:
    st.success("✅ All equipment are OK")
    st.dataframe(df_merge)
    zip_file = create_zip(
        st.session_state.df_down_process,
        st.session_state.df_op_process,
        down_name,
        op_name
    )
    st.dataframe(st.session_state.edited_down)    
    with col_zip:
        st.download_button(
            label="⬇️ Download validated files (.zip)",
            data=zip_file,
            file_name="validated_files.zip",
            mime="application/zip",
        )
    
    # NAVIGATION
    with col_back:
        if st.button("⬅️ Back"):
            st.switch_page("model.py")
    st.stop()

else:
    # =====================================================
    # CURRENT EQUIPMENT
    # =====================================================
    if "equipments" not in st.session_state or not st.session_state.equipments:
        st.session_state.equipments = problem["Equipment"].unique().tolist()

    if "current_index" not in st.session_state:
        st.session_state.current_index = 0

    # sécurité
    if len(st.session_state.equipments) == 0:
        st.warning("No equipments to process")
        st.stop()

    # clamp index propre
    st.session_state.current_index = min(
        st.session_state.current_index,
        len(st.session_state.equipments) - 1
    )
    equip = st.session_state.equipments[st.session_state.current_index]
    
    st.dataframe(problem)
    st.warning(
        f"⚠️ Correction : {equip}"
    )


    # =====================================================
    # DOWN GRID
    # =====================================================
    st.subheader("DOWN")
    edited_down = build_grid(
        st.session_state.df_down_process[
            st.session_state.df_down_process["Equip No"] == equip
        ].copy(), key="down_grid"
    )
    st.session_state.edited_down = edited_down

    # =====================================================
    # OP GRID
    # ===================================================== 
    st.subheader("OP")
    edited_op = build_grid(
        st.session_state.df_op_process[
            st.session_state.df_op_process["Equipment"] == equip
        ].copy(), key= "op_grid"
    )

    # st.write("edited_down")
    # st.dataframe(edited_down)

    # st.write("edited_op")
    # st.dataframe(edited_op)
    # =====================================================
    # SAVE
    # =====================================================
    if st.button("💾 Save and Next"):

        df_down = st.session_state.df_down_process
        df_op = st.session_state.df_op_process

        # 1. remove old lines
        df_down_validate = df_down[df_down["Equip No"] != equip]
        df_op_validate = df_op[df_op["Equipment"] != equip]

        # 2. add edited
        st.session_state.df_down_process = pd.concat(
            [df_down_validate, edited_down],
            ignore_index=True
        )

        st.session_state.df_op_process = pd.concat(
            [df_op_validate, edited_op],
            ignore_index=True
        )

        # 3. recompute KPI
        df_merge = check_kpis_value(
            df_down=st.session_state.df_down_process.copy(),
            df_op=st.session_state.df_op_process.copy()
        )

        problem = df_merge[df_merge["Used Hrs"] > df_merge["Calendar Hrs"]]

        # 4. rebuild equipment list
        new_list = problem["Equipment"].unique().tolist()
        st.session_state.equipments = new_list

        # 5. reset index PROPREMENT
        st.session_state.current_index = 0

        # 6. rerun
        st.rerun()