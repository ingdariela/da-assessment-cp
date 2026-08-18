import pandas as pd
import plotly.express as px
import streamlit as st

def render_data_profile_table(
    df: pd.DataFrame,
    col_name_label: str = "Column Name",
    data_type_label: str = "Data Type",
    non_null_label: str = "Non-Null Count",
    null_count_label: str = "Null Count",
    null_pct_label: str = "Null %",
    unique_label: str = "Unique Values",
    sample_label: str = "Sample Value",
):
    """Renders a comprehensive data profiling table in Streamlit with column

    data types, total non-null counts, null counts and percentages,
    unique value counts, and sample values.
    """
    if df is None or df.empty:
        st.warning("The provided DataFrame is empty or None.")
        return

    total_rows = len(df)
    null_counts = df.isna().sum().values
    non_null_counts = df.notna().sum().values
    null_percentages = (null_counts / total_rows * 100).round(2)

    profile_df = pd.DataFrame(
        {
            col_name_label: df.columns,
            data_type_label: df.dtypes.astype(str),
            non_null_label: non_null_counts,
            null_count_label: null_counts,
            null_pct_label: null_percentages,
            unique_label: df.nunique(dropna=False).values,
            sample_label: [
                str(df[col].dropna().iloc[0])
                if not df[col].dropna().empty
                else "N/A"
                for col in df.columns
            ],
        }
    )

    profile_df = profile_df.sort_values(by="Column Name")
    st.dataframe(
        profile_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            null_pct_label: st.column_config.NumberColumn(
                null_pct_label,
                format="%.2f%%",
            )
        },
    )

def render_timeseries_chart(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    title: str = "Time Series Analysis",
    group_by_col: str = None,
    by_customer_info: bool = False,
    freq: str = "D",  # 'D' (Día), 'W' (Semana), 'MS' (Inicio de Mes)
    agg_func: str = "sum",
):
    """Renders a standardized Plotly line chart, properly handling dates and subgroups."""
    if df is None or df.empty or date_col not in df.columns:
        st.warning("No data available to plot time series.")
        return

    data = df.copy()

    # Si se activa el flag o si envían 'YES'/'Yes', asignamos customer_info
    if (
        by_customer_info
        or (
            isinstance(by_customer_info, str)
            and by_customer_info.upper() == "YES"
        )
    ):
        group_by_col = "customer_info"

    # 1. Asegurar formato datetime sin horas para evitar inconsistencias
    data[date_col] = pd.to_datetime(data[date_col])

    # 2. Definir lista de columnas para el agrupamiento
    group_cols = [pd.Grouper(key=date_col, freq=freq)]
    if group_by_col and group_by_col in data.columns:
        group_cols.append(group_by_col)

    # 3. Agrupar y asegurar reseteo de índice
    aggregated_df = (
        data.groupby(group_cols)[value_col]
        .agg(agg_func)
        .reset_index()
    )

    # Convertir la columna de fecha explícitamente a string para que Plotly la grafique sin errores
    aggregated_df[date_col] = aggregated_df[date_col].dt.strftime('%Y-%m-%d')
    aggregated_df = aggregated_df.sort_values(by=date_col)

    # 4. Crear gráfico de Plotly
    color_param = group_by_col if (group_by_col and group_by_col in aggregated_df.columns) else None

    fig = px.line(
        aggregated_df,
        x=date_col,
        y=value_col,
        color=color_param,
        title=title,
        markers=True,
        template="plotly_white",
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=value_col.replace("_", " ").title(),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )

    config = {
        "displaylogo": False,
        "modeBarButtonsToRemove": ["toImage", "sendDataToCloud"],
    }

    st.plotly_chart(
        fig, use_container_width=True, config=config, key=f"ts_{title}"
    )
