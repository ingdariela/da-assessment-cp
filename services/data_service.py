import pandas as pd
import streamlit as st
import src.config as cg
import unicodedata
from src.database import DataLoader

def load_data():

    loader = DataLoader()
    engine = loader.engine

    accounts = pd.read_sql_table("atp_accounts", con=engine)
    orders = pd.read_sql_table("atp_orders", con=engine)
    
    ord_cols = orders.columns
    
    ord_grp = orders.groupby('order_id').size().reset_index(name='count_order')
    orders = pd.merge(orders, ord_grp, on='order_id')

    accounts = clean_data(accounts)
    orders = clean_data(orders)

    return accounts, orders, ord_cols


def clean_dataframe_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans all types of invisible/special spaces and collapses multiple internal spaces

    without triggering PyArrow regex errors.
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    def clean_text_value(val):
        if pd.isna(val) or val is None:
            return None

        # Convert to string
        text = str(val)

        # 1. Normaliza espacios invisibles Unicode (convierte \xa0, \u200b, etc., a espacios estándar ' ')
        text = unicodedata.normalize("NFKC", text)

        # 2. Colapsa múltiples espacios internos a 1 solo y quita bordes
        text = " ".join(text.split())

        # 3. Retorna limpio o None si quedó vacío
        return text if text else None

    for col in df.columns:
        # Detecta columnas de texto independientemente del backend (PyArrow / Python)
        if (
            pd.api.types.is_string_dtype(df[col])
            or df[col].dtype == "object"
            or str(df[col].dtype) in ["string", "category"]
        ):
            df[col] = df[col].apply(clean_text_value)

    return df

def clean_data(df):

    df = df.map(lambda x: x.upper() if isinstance(x, str) else x)
    df = clean_dataframe_strings(df)
    
    cleaned_series = df['region'].astype(str).str.strip().str.upper()
    df['region'] = cleaned_series.map(cg.region_mapping).fillna(df['region'])
    
    if "customer_name" in df.columns:
        split_cols = df['customer_name'].str.split(' - ', n=1, expand=True)
        df['customer_name'] = split_cols[0]
        df['customer_info'] = split_cols[1] if 1 in split_cols.columns else None
        
        df['parent_id'] = df['parent_id'].fillna(df['customer_id'])
        
        regions = df[['customer_id', 'region']].dropna().drop_duplicates()
        df = pd.merge(df, regions, on='customer_id', suffixes=('', '_y'))
        df['region'] = df['region'].fillna(df['region_y'])
        df = df.drop(columns=['region_y'])
                
    return df 
    

def merge_cx_data(accs, ords):
    ords = pd.merge(ords, accs, on='customer_id', suffixes=('', '_att')).sort_values("order_date")
    return ords

def filter_cx_data(ords, cx, energy_type=None, sel_region=None):
    if cx != 'ALL':
        ords = ords.query("customer_name == @cx").reset_index(drop=True)
    if energy_type and energy_type != 'ALL':
        ords = ords.query("energy_type == @energy_type").reset_index(drop=True)
    if energy_type and sel_region != 'ALL':
        ords = ords.query("region == @sel_region").reset_index(drop=True)
    return ords

def get_list_cx(accs, ords):
    
    ords_grp = ords.groupby('customer_id').size().reset_index(name='count')
    cxs = pd.merge(accs, ords_grp, on='customer_id')
    cxs = cxs.groupby('customer_name')['count'].sum().reset_index().sort_values(by='count', ascending=False)
    list_cxs = list(cxs['customer_name'])
    list_cxs = ['ALL'] + list_cxs
    
    return list_cxs

import pandas as pd


def get_orders_with_conflict_details(
    ords_clean: pd.DataFrame, id_col: str = "order_id"
) -> pd.DataFrame:
    """Detects duplicate IDs with conflicting numeric attributes and appends explicit

    'diff_<col>' numeric columns for metrics, alongside 'conflicting_columns'.
    """
    if ords_clean is None or ords_clean.empty or id_col not in ords_clean.columns:
        return pd.DataFrame()

    # Filter duplicate IDs directly using transform (more efficient than merge)
    counts = ords_clean.groupby(id_col)[id_col].transform("count")
    df = ords_clean[counts > 1].copy()

    if df.empty:
        return pd.DataFrame()

    # Filter numeric columns only (excluding ID)
    numeric_cols = [
        col
        for col in df.select_dtypes(include=["number"]).columns
        if col != id_col
    ]

    # Find unique count per column for each ID
    unique_counts = df.groupby(id_col)[numeric_cols].transform("nunique")
    has_conflict_mask = (unique_counts > 1).any(axis=1)
    conflicting_df = df[has_conflict_mask].copy()

    if conflicting_df.empty:
        return pd.DataFrame()

    conflicting_df[f"{id_col}_2"] = conflicting_df[id_col]

    # Calculate individual numeric differences and build text summary per group
    def process_group_conflicts(group):
        changed = []
        for col in numeric_cols:
            if group[col].nunique(dropna=False) > 1:
                valid_nums = group[col].dropna()
                if not valid_nums.empty:
                    diff_val = round(
                        abs(valid_nums.max() - valid_nums.min()), 4
                    )
                    changed.append(f"{col} (diff={diff_val})")
                    group[f"diff_{col}"] = diff_val
                else:
                    changed.append(f"{col} (contains None)")
                    group[f"diff_{col}"] = 0.0
            else:
                group[f"diff_{col}"] = 0.0

        group["conflicting_columns"] = ", ".join(changed)
        return group

    conflicting_df = conflicting_df.groupby(id_col, group_keys=False).apply(
        process_group_conflicts
    )

    conflicting_df = conflicting_df.rename(
        {f"{id_col}_2": f"{id_col}"}, axis=1
    )

    # Identify created diff columns to place them right after 'conflicting_columns'
    diff_cols = [f"diff_{col}" for col in numeric_cols]

    # Reorder columns: ID -> conflicting_columns -> diff_cols -> rest of dataframe
    other_cols = [
        c
        for c in conflicting_df.columns
        if c not in [id_col, "conflicting_columns"] + diff_cols
    ]

    cols = [id_col,  "diff_billed_rate", "diff_qty_ordered", "diff_qty_delivered", "billed_rate", "qty_ordered", "qty_delivered"]
    return conflicting_df[cols]



