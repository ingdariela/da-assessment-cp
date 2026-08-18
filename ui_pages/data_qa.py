import pandas as pd
import streamlit as st
import services.data_service as data_service
import services.plot_service as plot_service
import services.ui_service as ui_service
import plotly.express as px
import numpy as np
import warnings
warnings.filterwarnings("ignore")

def app():

    accs_raw = st.session_state["accs_raw"].copy()
    ords_raw = st.session_state["ords_raw"].copy()
    accs_clean= st.session_state["accs_clean"].copy()
    ords_clean = st.session_state["ords_clean"].copy()
    cx = st.session_state["cx"]
    ords_cols = st.session_state["ords_cols"].copy()

    st.header("Data Quality & Profiling")

    # 3. SECTION 2: Tabs
    ui_service.render_dataset_audit_section_tabs(
        titles=["Accounts", "Orders"],
        raw_dfs=(accs_raw, ords_raw[ords_cols]),
        clean_dfs=(accs_clean, ords_clean[ords_cols]),
        plot_service=plot_service
    )