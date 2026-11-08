import streamlit as st

from backend.packages.kips import check_kpis_value

df_merge = check_kpis_value(
    df_down=st.session_state.df_down,
    df_op=st.session_state.df_op
)
st.write(
    f"### {st.session_state.df_down.Minesite.unique()} site Operating Hours vs Downtime Hours"
)
st.dataframe(df_merge)

# =====================================================
# NAVIGATION
# =====================================================
col_back, col_dpp = st.columns([9, 1])
with col_back:
    if st.button("⬅️ Back"):
        st.switch_page("model.py")