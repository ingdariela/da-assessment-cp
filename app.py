import streamlit as st
from streamlit_option_menu import option_menu
import ui_pages.data_qa as dqa
import ui_pages.finops as finops
import services.data_service as data_service
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
        .css-164nlkn { padding-top: 0px !important; padding-bottom: 0px !important; margin-bottom: -20px !important; }
        .css-18e3th9 { padding-top: 0px !important; }
      
    </style>
    """,
    unsafe_allow_html=True
)

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
            "color": "black",
            "font-size": "25px",
            "border-radius": "5px",
            "padding": "5px 10px",
            "margin": "0px",
        },
        "nav-link-0-selected": {"background-color": "#33A8FF"},
        "nav-link-1": {"background-color": "#33A8FF"},
        "nav-link-2": {"background-color": "#33FF57"},
        "nav-link-3": {"background-color": "#FF33A8"},
        "nav-link-selected": {
            "background-color": "#bebdbdff",
            "color": "black",
            "font-size": "25px",
            "border-radius": "5px",
            "--icon-color": "white",
        },
    },
)


with open('./styles/style_main.css', 'r') as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=86400, show_spinner="Consulting Database...")
def get_load_data():
    accs_raw, ords_raw, ords_cols = data_service.load_data()
    accs_clean = accs_raw.drop_duplicates('customer_id').reset_index(drop=True)
    ords_clean = ords_raw.drop_duplicates('order_id').reset_index(drop=True)
    return accs_raw, ords_raw, accs_clean, ords_clean, ords_cols

if "first_run" not in st.session_state:
    st.session_state.first_run = True
else:
    st.session_state.first_run = False

    
# if st.session_state.first_run:
#     accs_raw, ords_raw, accs_clean, ords_clean, ords_cols = get_load_data()
# else:
#     accs_raw, ords_raw, ords_cols = data_service.load_data()
#     accs_clean = accs_raw.drop_duplicates('customer_id').reset_index(drop=True)
#     ords_clean = ords_raw.drop_duplicates('order_id').reset_index(drop=True)

accs_raw, ords_raw, accs_clean, ords_clean, ords_cols = get_load_data()

st.write(st.session_state.first_run)
cxs = data_service.get_list_cx(accs_clean, ords_clean)
ords_raw = data_service.merge_cx_data(accs_clean, ords_raw)
ords_clean= data_service.merge_cx_data(accs_clean, ords_clean)

list_energy_type = ['ALL'] + list(ords_clean['energy_type'].unique())
list_regions = ['ALL'] + list(ords_clean['region'].unique())

with st.sidebar:
    cx = st.selectbox("**Select Customer**", cxs)
    energy_type = st.selectbox("**Select Energy Type**", list_energy_type)
    sel_region = st.selectbox("**Select Region**", list_regions)
    
accs_raw_filt = data_service.filter_cx_data(accs_raw, cx)
accs_clean_filt = data_service.filter_cx_data(accs_clean, cx)

ords_raw_filt = data_service.filter_cx_data(ords_raw, cx, energy_type, sel_region)
ords_clean_filt = data_service.filter_cx_data(ords_clean, cx, energy_type, sel_region)

st.session_state['accs_raw'] = accs_raw_filt
st.session_state['ords_raw'] = ords_raw_filt

st.session_state['accs_clean'] = accs_clean_filt
st.session_state['ords_clean'] = ords_clean_filt

st.session_state['cx'] = cx
st.session_state['ords_cols'] = ords_cols

# =========================================================================
# BANNER INFORMATIVO: CUSTOMER CONTEXT SUMMARY
# =========================================================================
if cx and cx != "All":
    # 1. Cálculo de porcentaje de volumen de órdenes respecto al total global (sin filtrar)
    total_global_orders = len(ords_clean) if ords_clean is not None else 0
    cx_orders_count = len(ords_clean_filt) if ords_clean_filt is not None else 0
    vol_pct = (cx_orders_count / total_global_orders * 100) if total_global_orders > 0 else 0.0

    # 2. Extracción de Regiones
    if 'region' in ords_clean_filt.columns and not ords_clean_filt['region'].dropna().empty:
        regions_list = ", ".join(ords_clean_filt['region'].dropna().unique().astype(str))
    elif 'region' in ords_clean_filt.columns and not ords_clean_filt['region'].dropna().empty:
        regions_list = ", ".join(ords_clean_filt['region'].dropna().unique().astype(str))
    else:
        regions_list = "N/A"

    # 3. Extracción de Rate Categories
    if 'rate_category' in ords_clean_filt.columns and not ords_clean_filt['rate_category'].dropna().empty:
        categories_list = ", ".join(ords_clean_filt['rate_category'].dropna().unique().astype(str))
    else:
        categories_list = "N/A"

    # 4. Renderizado del Banner de Contexto
    st.info(
        f"👤 **Customer Selected:** {cx} | "
        f"📦 **Order Volume Share:** {vol_pct:.1f}% ({cx_orders_count:,} orders) | "
        f"🌍 **Regions:** {regions_list} | "
        f"🏷️ **Rate Categories:** {categories_list}"
    )


if app == "Data Quality Audit":
    dqa.app()
elif app == "FinOps Analysis":
    finops.app()
