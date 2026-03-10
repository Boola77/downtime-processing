# codingf:utf-8

import streamlit as st

st.title("Page de Test  Aigain")

# Init
if "step" not in st.session_state:
    st.session_state.step = 0

# ----- Dialog 1 ------
@st.dialog("Première fenêtre")
def dialog1():
    st.write("Ceci est le premier dialog")
    if st.button("Aller au suivant"):
        st.session_state.step = 2
        st.rerun()
    
# ------ Dialog 2 --------
@st.dialog("Deuxièmes fenêtre")
def dialog2():
    st.write("Ceci est le deuxième dialogue")
    if st.button("Aller au troisième"):
        st.session_state.step = 3
        st.rerun()

# --------Dialog 3 -------
@st.dialog("Troisième fenêtre")
def dialog3():
    st.write("Ceci est le troisième dialogue")
    if st.button("Fin du processus"):
        st.session_state.step = 0
        st.rerun()

# ------- Bouton principle -------
if st.button("Ouvrir le workflow"):
    st.session_state.step = 1

# --------- Contrôle affichage ---------
if st.session_state.step == 1:
    dialog1()

elif st.session_state.step == 2:
    dialog2()

elif st.session_state.step == 3:
    dialog3()

# st.session_state.step = 0