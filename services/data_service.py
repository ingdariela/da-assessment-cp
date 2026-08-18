import unicodedata
import pandas as pd
import src.config as cg
from src.database import DataLoader
import streamlit as st

def load_data():
    loader = DataLoader()
    engine = loader.engine

    accounts = pd.read_sql_table("atp_accounts", con=engine)
    orders = pd.read_sql_table("atp_orders", con=engine)
    ord_cols = orders.columns
    
    accounts['is_anchor'] = accounts['is_anchor'].apply(lambda x: False if x == 0 else True)
    accounts['active'] = accounts['active'].apply(lambda x: False if x == 0 else True)

    ord_grp = orders.groupby('order_id').size().reset_index(name='count_order')
    orders = pd.merge(orders, ord_grp, on='order_id')

    return clean_data(accounts), clean_data(orders), ord_cols

def clean_dataframe_strings(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()
    str_cols = df.select_dtypes(include=['object', 'string', 'category']).columns

    for col in str_cols:
        df[col] = df[col].astype(str).apply(
            lambda x: " ".join(unicodedata.normalize("NFKC", x).split()) if pd.notna(x) and x != 'nan' else None
        )
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.map(lambda x: x.upper() if isinstance(x, str) else x)
    df = clean_dataframe_strings(df)

    if 'region' in df.columns:
        df['region'] = df['region'].astype(str).str.strip().str.upper().map(cg.region_mapping).fillna(df['region'])

    if "customer_name" in df.columns:
        split_cols = df['customer_name'].str.split(' - ', n=1, expand=True)
        df['customer_name'] = split_cols[0]
        df['customer_info'] = split_cols[1] if 1 in split_cols.columns else None
        df['parent_id'] = df['parent_id'].fillna(df['customer_id'])

        regions = df[['customer_id', 'region']].dropna().drop_duplicates()
        df = pd.merge(df, regions, on='customer_id', suffixes=('', '_y'))
        df['region'] = df['region'].fillna(df.pop('region_y'))
        
    else:
        df.loc[
           df.query(
                "qty_ordered == qty_delivered & qty_delivered > 0 & qty_ordered.notna()"
            ).index,
            "status",
        ] = "DELIVERED"

    return df

def merge_cx_data(accs: pd.DataFrame, ords: pd.DataFrame) -> pd.DataFrame:
    return pd.merge(ords, accs, on='customer_id', suffixes=('', '_att')).sort_values("order_date")

def filter_cx_data(ords: pd.DataFrame, cx: str, energy_type: str = None, sel_region: str = None) -> pd.DataFrame:
    query_parts = []
    if cx and cx != 'ALL':
        query_parts.append(f"customer_name == '{cx}'")
    if energy_type and energy_type != 'ALL':
        query_parts.append(f"energy_type == '{energy_type}'")
    if sel_region and sel_region != 'ALL':
        query_parts.append(f"region == '{sel_region}'")

    return ords.query(" and ".join(query_parts)).reset_index(drop=True) if query_parts else ords

def get_list_cx(accs: pd.DataFrame, ords: pd.DataFrame) -> list:
    ords_grp = ords.groupby('customer_id').size().reset_index(name='count')
    cxs = pd.merge(accs, ords_grp, on='customer_id').groupby('customer_name')['count'].sum().reset_index().sort_values(by='count', ascending=False)
    return ['ALL'] + list(cxs['customer_name'])

def get_orders_with_conflict_details(ords_clean: pd.DataFrame, id_col: str = "order_id") -> pd.DataFrame:
    if ords_clean is None or ords_clean.empty or id_col not in ords_clean.columns:
        return pd.DataFrame()

    counts = ords_clean.groupby(id_col)[id_col].transform("count")
    df = ords_clean[counts > 1].copy()
    if df.empty:
        return pd.DataFrame()

    numeric_cols = [col for col in df.select_dtypes(include=["number"]).columns if col != id_col]
    unique_counts = df.groupby(id_col)[numeric_cols].transform("nunique")
    conflicting_df = df[(unique_counts > 1).any(axis=1)].copy()

    conflicting_df['aux'] = conflicting_df[id_col]

    if conflicting_df.empty:
        return pd.DataFrame()

    def process_group_conflicts(group):
        changed = []
        for col in numeric_cols:
            if group[col].nunique(dropna=False) > 1:
                valid_nums = group[col].dropna()
                diff_val = round(abs(valid_nums.max() - valid_nums.min()), 4) if not valid_nums.empty else 0.0
                changed.append(f"{col} (diff={diff_val})")
                group[f"diff_{col}"] = diff_val
            else:
                group[f"diff_{col}"] = 0.0
        group["conflicting_columns"] = ", ".join(changed)
        return group

    conflicting_df = conflicting_df.groupby(id_col, group_keys=False).apply(process_group_conflicts)
    conflicting_df = conflicting_df.rename(columns={'aux':id_col})

    cols = [id_col, "diff_billed_rate", "diff_qty_ordered", "diff_qty_delivered", "billed_rate", "qty_ordered", "qty_delivered"]
    return conflicting_df[[c for c in cols if c in conflicting_df.columns]]