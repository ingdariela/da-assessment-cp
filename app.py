import warnings
import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

import services.data_service as data_service
import ui_pages.data_qa as dqa
import ui_pages.finops as finops

warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

# CSS Injection
st.markdown(
    """
    <style>
        .css-164nlkn { padding-top: 0px !important; padding-bottom: 0px !important; margin-bottom: -20px !important; }
        .css-18e3th9 { padding-top: 0px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

try:
    with open('./styles/style_main.css', 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Navigation Menu
app = option_menu(
    menu_title=None,
    options=['Data Quality Audit', 'FinOps Analysis'],
    menu_icon='cast',
    default_index=0,
    orientation='horizontal',
    styles={
        "container": {"background-color": "#F5F5F5", "border-radius": "10px", "width": "100%"},
        "icon": {"color": "black", "font-size": "18px"},
        "nav-link": {
            "color": "black", "font-size": "25px", "border-radius": "5px",
            "padding": "5px 10px", "margin": "0px"
        },
        "nav-link-selected": {
            "background-color": "#bebdbdff", "color": "black",
            "font-size": "25px", "border-radius": "5px", "--icon-color": "white"
        },
    },
)

@st.cache_data(ttl=86400, show_spinner="Consulting Database...")
def get_load_data():
    accs_raw, ords_raw, ords_cols = data_service.load_data()
    accs_clean = accs_raw.drop_duplicates('customer_id').reset_index(drop=True)
    ords_clean = ords_raw.drop_duplicates('order_id').reset_index(drop=True)
    return accs_raw, ords_raw, accs_clean, ords_clean, ords_cols

# Data loading & session setup
accs_raw, ords_raw, accs_clean, ords_clean, ords_cols = get_load_data()

cxs = data_service.get_list_cx(accs_clean, ords_clean)
ords_raw = data_service.merge_cx_data(accs_clean, ords_raw)
ords_clean = data_service.merge_cx_data(accs_clean, ords_clean)

# Sidebar Filters
with st.sidebar:
    cx = st.selectbox("**Select Customer**", cxs)
    energy_type = st.selectbox("**Select Energy Type**", ['ALL'] + list(ords_clean['energy_type'].unique()))
    sel_region = st.selectbox("**Select Region**", ['ALL'] + list(ords_clean['region'].unique()))

# Filtered Datasets
st.session_state.update({
    'accs_raw': data_service.filter_cx_data(accs_raw, cx),
    'accs_clean': data_service.filter_cx_data(accs_clean, cx),
    'ords_raw': data_service.filter_cx_data(ords_raw, cx, energy_type, sel_region),
    'ords_clean': data_service.filter_cx_data(ords_clean, cx, energy_type, sel_region),
    'cx': cx,
    'ords_cols': ords_cols
})

# Context Banner
if cx and cx != "ALL":
    ords_clean_filt = st.session_state['ords_clean']
    total_global_orders = len(ords_clean) if ords_clean is not None else 0
    cx_orders_count = len(ords_clean_filt) if ords_clean_filt is not None else 0
    vol_pct = (cx_orders_count / total_global_orders * 100) if total_global_orders > 0 else 0.0

    regions_list = ", ".join(ords_clean_filt['region'].dropna().unique().astype(str)) if 'region' in ords_clean_filt.columns and not ords_clean_filt['region'].dropna().empty else "N/A"
    categories_list = ", ".join(ords_clean_filt['rate_category'].dropna().unique().astype(str)) if 'rate_category' in ords_clean_filt.columns and not ords_clean_filt['rate_category'].dropna().empty else "N/A"

    st.info(
        f"👤 **Customer Selected:** {cx} | "
        f"📦 **Order Volume Share:** {vol_pct:.1f}% ({cx_orders_count:,} orders) | "
        f"🌍 **Regions:** {regions_list} | "
        f"🏷️ **Rate Categories:** {categories_list}"
    )

# Page Routing
if app == "Data Quality Audit":
    dqa.app()
elif app == "FinOps Analysis":
    finops.app()