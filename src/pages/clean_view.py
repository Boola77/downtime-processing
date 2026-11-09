import streamlit as st
import os
import pandas as pd

from backend.packages.kips import check_kpis_value

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


df_merge = check_kpis_value(
    df_down=st.session_state.df_down,
    df_op=st.session_state.df_op
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

browser_path = os.path.join(
    os.path.dirname(BASE_DIR),
    "data",
    "Equipments",
    "Equipment Browser_v3.csv"
)

if not os.path.exists(browser_path):
    st.error(f"File not found: {browser_path}")
else:
    # ⚡ cached read
    df_browser = load_browser(browser_path)

if "browser_path" not in st.session_state:
    st.session_state.browser_path = browser_path

if "df_browser" not in st.session_state:
    st.session_state.df_browser = df_browser

df_site = st.session_state.df_browser
minesites = st.session_state.df_down["Minesite"].dropna().unique()

if len(minesites) > 0:
    minesite = str(minesites[0]).strip().lower()

    df_site = df_site[
        df_site["Minesite"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq(minesite)
    ].reset_index(drop=True)

df_site = df_site[
    ['Equipment', 'On Site Id', "SerialNumber", 'Model', "Parent Product Family", "Status"]
]

df_merge = df_merge.merge(df_site, on="Equipment", how="left")

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