import streamlit as st
import pandas as pd
import plotly.express as px
from services.plot_service import render_timeseries_chart

def render_finops_page(df_orders: pd.DataFrame, df_accounts: pd.DataFrame):
    st.title("Operational & Financial Impact Analysis (FinOps)")
    st.caption("Reconciliation and Migration Impact Assessment")

    if df_orders is None or df_orders.empty:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
        return

    # Unir con la tabla de cuentas si es necesario
    if df_accounts is not None and not df_accounts.empty and 'customer_name' not in df_orders.columns:
        df_working = df_orders.merge(
            df_accounts[['customer_id', 'customer_name', 'is_anchor', 'tier', 'region']], 
            on='customer_id', 
            how='left'
        )
    else:
        df_working = df_orders.copy()

    # Formatos de fecha y aseguramiento de tipos
    df_working['order_date'] = pd.to_datetime(df_working['order_date'])

    # --- CÁLCULOS FINANCIEROS Y OPERATIVOS ---
    df_working['billed_amount'] = df_working['qty_delivered'] * df_working['billed_rate']
    df_working['contracted_amount'] = df_working['qty_delivered'] * df_working['contracted_rate']
    df_working['financial_discrepancy'] = df_working['billed_amount'] - df_working['contracted_amount']
    df_working['volume_fulfillment_pct'] = (df_working['qty_delivered'] / df_working['qty_ordered'].replace(0, pd.NA)) * 100

    # Identificar columna de era (PRE / POST)
    era_col = 'migration_status' if 'migration_status' in df_working.columns else 'system_era'
    if era_col not in df_working.columns:
        df_working[era_col] = df_working['order_date'].apply(
            lambda x: 'PRE' if x < pd.Timestamp('2024-10-01') else 'POST'
        )

    # Subsets
    df_pre = df_working[df_working[era_col] == 'PRE']
    df_post = df_working[df_working[era_col] == 'POST']

    # Conteo de meses para promedios
    pre_months = max(df_pre['order_date'].dt.to_period('M').nunique(), 1) if not df_pre.empty else 1
    post_months = max(df_post['order_date'].dt.to_period('M').nunique(), 1) if not df_post.empty else 1

    # --- ESTRUCTURA EN TABS ---
    tab_volume, tab_billing, tab_duplicates, tab_segmentation = st.tabs([
        "📦 Volume & Operations Explorer", 
        "💰 Billing & Rates Explorer", 
        "⚠️ Data Integrity & Duplicates",
        "👥 Customer Segmentation & Tiers"
    ])
    
    # =========================================================================
    # TAB 1: VOLUMEN OPERATIVO Y CUMPLIMIENTO (CTO FOCUS)
    # =========================================================================
    with tab_volume:
        st.subheader("Operational Volume & Delivery Performance Summary")

        # --- CÁLCULOS DE VOLUMEN ---
        tot_ordered = df_working['qty_ordered'].sum()
        tot_delivered = df_working['qty_delivered'].sum()
        tot_fulfillment = df_working['volume_fulfillment_pct'].mean() if not df_working.empty else 0.0

        pre_ordered = df_pre['qty_ordered'].sum()
        pre_delivered = df_pre['qty_delivered'].sum()
        pre_fulfillment = df_pre['volume_fulfillment_pct'].mean() if not df_pre.empty else 0.0

        post_ordered = df_post['qty_ordered'].sum()
        post_delivered = df_post['qty_delivered'].sum()
        post_fulfillment = df_post['volume_fulfillment_pct'].mean() if not df_post.empty else 0.0

        # --- ESTRUCTURA EN 3 COLUMNAS ---
        v_col_tot, v_col_pre, v_col_post = st.columns(3)

        with v_col_tot:
            st.markdown("### 📊 Total Dataset")
            st.metric("Total Ordered", f"{tot_ordered:,.0f} units")
            st.metric("Total Delivered", f"{tot_delivered:,.0f} units")
            st.metric("Avg Fulfillment Rate", f"{tot_fulfillment:.1f}%")

        with v_col_pre:
            st.markdown(f"### 🔵 PRE-Migration ({pre_months} Mos)")
            st.metric("PRE Ordered", f"{pre_ordered:,.0f} units")
            st.metric("PRE Delivered", f"{pre_delivered:,.0f} units")
            st.metric("PRE Fulfillment Rate", f"{pre_fulfillment:.1f}%")

        with v_col_post:
            st.markdown(f"### 🟠 POST-Migration ({post_months} Mos)")
            st.metric("POST Ordered", f"{post_ordered:,.0f} units")
            st.metric("POST Delivered", f"{post_delivered:,.0f} units")
            fulfillment_diff = post_fulfillment - pre_fulfillment
            st.metric(
                "POST Fulfillment Rate", 
                f"{post_fulfillment:.1f}%", 
                delta=f"{fulfillment_diff:+.1f}% vs PRE"
            )

        st.divider()

        # --- SECCIÓN OPERATIVA AVANZADA CON SERIES DE TIEMPO ---
        st.subheader("Operational Performance & Order Lifecycle Analytics")

        col_ops1, col_ops2 = st.columns(2)

        with col_ops1:
            st.markdown("**1. Monthly Fulfillment Rate & Delivery Gap Trend**")
            
            # Agrupación mensual de volúmenes
            df_monthly_ops = (
                df_working.groupby(pd.Grouper(key='order_date', freq='MS'))[['qty_ordered', 'qty_delivered']]
                .sum()
                .reset_index()
            )
            
            # Cálculo de la tasa de cumplimiento (%)
            df_monthly_ops['fulfillment_rate'] = (
                (df_monthly_ops['qty_delivered'] / df_monthly_ops['qty_ordered'].replace(0, pd.NA)) * 100
            ).fillna(0.0)
            
            df_monthly_ops['formatted_date'] = df_monthly_ops['order_date'].dt.strftime('%Y-%m-%d')

            fig_fulfill_trend = px.line(
                df_monthly_ops,
                x='formatted_date',
                y='fulfillment_rate',
                custom_data=['qty_ordered', 'qty_delivered'],
                labels={'fulfillment_rate': 'Fulfillment Rate (%)', 'formatted_date': 'Order Month'},
                title="Monthly Fulfillment Rate Trend (%)",
                template="plotly_white"
            )

            fig_fulfill_trend.update_traces(
                line=dict(color='#008080', width=2.5),
                hovertemplate=(
                    "<b>Month:</b> %{x}<br>" +
                    "<b>Fulfillment Rate:</b> %{y:.2f}%<br>" +
                    "<b>Ordered:</b> %{customdata[0]:,.0f} units<br>" +
                    "<b>Delivered:</b> %{customdata[1]:,.0f} units<extra></extra>"
                )
            )

            # Línea de referencia de migración
            fig_fulfill_trend.add_vline(x="2024-10-01", line_width=2, line_dash="dash", line_color="red")
            fig_fulfill_trend.add_annotation(
                x="2024-10-01", y=1.05, yref="paper",
                text="Migration Date (Oct 2024)", showarrow=False, font=dict(color="red", size=10)
            )

            fig_fulfill_trend.update_layout(yaxis_ticksuffix="%", yaxis_tickformat=".1f", margin=dict(l=0, r=10, t=30, b=0))
            st.plotly_chart(fig_fulfill_trend, use_container_width=True)

        with col_ops2:
            st.markdown("**2. Order Status Distribution Relative Comparison (100% Stacked)**")
            
            # Agrupación por Era y Status
            status_era = (
                df_working.groupby([era_col, 'status'])['order_id']
                .count()
                .reset_index(name='order_count')
            )
            
            # Calcular % dentro de cada Era
            era_totals = status_era.groupby(era_col)['order_count'].transform('sum')
            status_era['status_pct'] = (status_era['order_count'] / era_totals) * 100

            fig_status = px.bar(
                status_era,
                x=era_col,
                y='status_pct',
                color='status',
                custom_data=['order_count'],
                labels={'status_pct': 'Percentage of Total Orders (%)', era_col: 'Era', 'status': 'Status'},
                title="Order Status Mix (PRE vs POST)",
                color_discrete_map={
                    'DELIVERED': '#2ca02c',
                    'PARTIAL': '#ff7f0e',
                    'FAILED': '#d62728',
                    'PENDING': '#1f77b4'
                },
                template="plotly_white"
            )

            fig_status.update_traces(
                hovertemplate=(
                    "<b>Era:</b> %{x}<br>" +
                    "<b>Status:</b> %{fullData.name}<br>" +
                    "<b>Share:</b> %{y:.2f}%<br>" +
                    "<b>Order Count:</b> %{customdata[0]:,.0f}<extra></extra>"
                )
            )

            fig_status.update_layout(yaxis_ticksuffix="%", margin=dict(l=0, r=10, t=30, b=0))
            st.plotly_chart(fig_status, use_container_width=True)

    # =========================================================================
    # TAB 2: FACTURACIÓN, TARIFAS Y DISCREPANCIAS (CFO FOCUS)
    # =========================================================================
    with tab_billing:
        st.subheader("Billing Reconciliation & Rate Discrepancies")

        # --- CÁLCULOS DENTRO DEL TAB DE FACTURACIÓN ---
        tot_billed = df_working['billed_amount'].sum()
        tot_contracted = df_working['contracted_amount'].sum()
        tot_discrepancy = df_working['financial_discrepancy'].sum()
        tot_disc_pct = (tot_discrepancy / tot_contracted * 100) if tot_contracted > 0 else 0.0

        pre_billed = df_pre['billed_amount'].sum()
        pre_contracted = df_pre['contracted_amount'].sum()
        pre_discrepancy = df_pre['financial_discrepancy'].sum()
        pre_disc_pct = (pre_discrepancy / pre_contracted * 100) if pre_contracted > 0 else 0.0
        pre_monthly_billed = pre_billed / pre_months

        post_billed = df_post['billed_amount'].sum()
        post_contracted = df_post['contracted_amount'].sum()
        post_discrepancy = df_post['financial_discrepancy'].sum()
        post_disc_pct = (post_discrepancy / post_contracted * 100) if post_contracted > 0 else 0.0
        post_monthly_billed = post_billed / post_months

        # --- CÁLCULO DE RUN-RATE LEAKAGE ---
        post_monthly_leakage = post_discrepancy / post_months
        annual_runrate_leakage = post_monthly_leakage * 12

        # --- SECCIÓN DE RESUMEN EJECUTIVO (KPIs REESTRUCTURADOS) ---
        col_tot, col_pre, col_post = st.columns(3)

        with col_tot:
            st.markdown("### 📊 Total Dataset")
            st.metric("Total Billed", f"${tot_billed:,.2f}")
            st.metric("Expected Contracted", f"${tot_contracted:,.2f}")
            st.metric("Net Discrepancy", f"${tot_discrepancy:,.2f}", delta=f"{tot_disc_pct:.2f}% vs Contracted", delta_color="off")

        with col_pre:
            st.markdown(f"### 🔵 PRE-Migration ({pre_months} Mos)")
            st.metric("PRE Billed", f"${pre_billed:,.2f}")
            st.metric("PRE Contracted", f"${pre_contracted:,.2f}")
            st.metric("PRE Discrepancy", f"${pre_discrepancy:,.2f}", delta=f"{pre_disc_pct:.2f}% vs Contracted", delta_color="off")
            st.caption(f"📅 Monthly Run-rate: **${pre_monthly_billed:,.2f}/mo**")

        with col_post:
            st.markdown(f"### 🟠 POST-Migration ({post_months} Mos)")
            st.metric("POST Billed", f"${post_billed:,.2f}")
            st.metric("POST Contracted", f"${post_contracted:,.2f}")
            st.metric("POST Discrepancy", f"${post_discrepancy:,.2f}", delta=f"{post_disc_pct:.2f}% vs Contracted", delta_color="off")
            monthly_runrate_diff = post_monthly_billed - pre_monthly_billed
            st.caption(f"📅 Monthly Run-rate: **${post_monthly_billed:,.2f}/mo** ({monthly_runrate_diff:+,.2f} vs PRE)")

        

        st.warning(
            f"💸 **Annualized Run-Rate Leakage:** At the current POST-migration discrepancy rate, "
            f"unaddressed billing variances project an annual revenue leakage of "
            f"**&#36;{annual_runrate_leakage:,.2f}/year** (~**&#36;{post_monthly_leakage:,.2f}/month**)."
        )

        st.divider()
        
        # --- ANÁLISIS DE FACTURACIÓN Y LÍNEA DE MIGRACIÓN ---
        col_cfo1, col_cfo2 = st.columns([2, 1])

        with col_cfo1:

            # --- PREPARACIÓN DE DATOS MENSUALES ---
            df_monthly_fin = (
                df_working.groupby(pd.Grouper(key='order_date', freq='MS'))[['billed_amount', 'contracted_amount', 'financial_discrepancy']]
                .sum()
                .reset_index()
            )

            # Cálculo de la discrepancia porcentual
            df_monthly_fin['discrepancy_pct'] = (
                (df_monthly_fin['financial_discrepancy'] / df_monthly_fin['contracted_amount'].replace(0, pd.NA)) * 100
            ).fillna(0.0)

            df_monthly_fin['formatted_date'] = df_monthly_fin['order_date'].dt.strftime('%Y-%m-%d')

            # =================================================================
            # GRÁFICO 1: TENDENCIA EN DÓLARES ($)
            # =================================================================
            fig_fin_usd = px.line(
                df_monthly_fin,
                x='formatted_date',
                y=['billed_amount', 'contracted_amount'],
                labels={'value': 'Amount ($)', 'variable': 'Type', 'formatted_date': 'Order Month'},
                title="1. Billed vs. Contracted Revenue Trend ($)",
                template="plotly_white"
            )

            fig_fin_usd.add_vline(
                x="2024-10-01", 
                line_width=2, 
                line_dash="dash", 
                line_color="red"
            )
            fig_fin_usd.add_annotation(
                x="2024-10-01", 
                y=1.05, 
                yref="paper",
                text="Migration Date (Oct 2024)", 
                showarrow=False, 
                font=dict(color="red", size=10)
            )

            fig_fin_usd.update_layout(
                yaxis_tickprefix="$",
                yaxis_tickformat=",.",
                margin=dict(l=0, r=10, t=30, b=10)
            )

            st.plotly_chart(fig_fin_usd, use_container_width=True)

            # =================================================================
            # GRÁFICO 2: TENDENCIA EN PORCENTAJE (%) [DEBAJO DEL PRIMERO]
            # =================================================================
            fig_fin_pct = px.line(
                df_monthly_fin,
                x='formatted_date',
                y='discrepancy_pct',
                custom_data=['financial_discrepancy', 'billed_amount', 'contracted_amount'],
                labels={'discrepancy_pct': 'Discrepancy (%)', 'formatted_date': 'Order Month'},
                title="2. Monthly Financial Discrepancy (%)",
                template="plotly_white"
            )

            fig_fin_pct.update_traces(
                line=dict(color='#2b5c8f', width=2.5),
                hovertemplate=(
                    "<b>Month:</b> %{x}<br>" +
                    "<b>Discrepancy (%):</b> %{y:.2f}%<br>" +
                    "<b>Discrepancy ($):</b> $%{customdata[0]:,.2f}<br>" +
                    "<b>Billed:</b> $%{customdata[1]:,.2f}<br>" +
                    "<b>Contracted:</b> $%{customdata[2]:,.2f}<extra></extra>"
                )
            )

            fig_fin_pct.add_vline(
                x="2024-10-01", 
                line_width=2, 
                line_dash="dash", 
                line_color="red"
            )
            fig_fin_pct.add_annotation(
                x="2024-10-01", 
                y=1.05, 
                yref="paper",
                text="Migration Date (Oct 2024)", 
                showarrow=False, 
                font=dict(color="red", size=10)
            )

            fig_fin_pct.update_layout(
                yaxis_ticksuffix="%",
                yaxis_tickformat=".1f",
                margin=dict(l=0, r=10, t=30, b=0)
            )

            st.plotly_chart(fig_fin_pct, use_container_width=True)

        with col_cfo2:

            if 'rate_category' in df_working.columns:
                # 1. Group amounts to calculate relative percentage by Era and Category
                rate_era_disc = (
                    df_working.groupby(['rate_category', era_col])[['financial_discrepancy', 'contracted_amount', 'billed_amount']]
                    .sum()
                    .reset_index()
                )

                # 2. Calculate discrepancy percentage over contracted amount
                rate_era_disc['discrepancy_pct'] = (
                    (rate_era_disc['financial_discrepancy'] / rate_era_disc['contracted_amount'].replace(0, pd.NA)) * 100
                ).fillna(0.0)

                # 3. Chart with % on the X axis and dollar amounts ($) in the Hover Tooltip
                fig_rate_disc = px.bar(
                    rate_era_disc,
                    x='discrepancy_pct',
                    y='rate_category',
                    color=era_col,
                    barmode='group',
                    orientation='h',
                    custom_data=['financial_discrepancy', 'billed_amount', 'contracted_amount'],
                    labels={
                        'discrepancy_pct': 'Discrepancy (%)',
                        'rate_category': 'Rate Category',
                        era_col: 'Era'
                    },
                    title="Discrepancy (%) vs Contracted by Category",
                    color_discrete_map={'PRE': '#1f77b4', 'POST': '#ff7f0e'},
                    template="plotly_white"
                )

                # 4. Custom Hover Tooltip in English
                fig_rate_disc.update_traces(
                    hovertemplate=(
                        "<b>Category:</b> %{y}<br>" +
                        "<b>Era:</b> %{fullData.name}<br>" +
                        "<b>Discrepancy (%):</b> %{x:.2f}%<br>" +
                        "<b>Discrepancy ($):</b> $%{customdata[0]:,.2f}<br>" +
                        "<b>Billed:</b> $%{customdata[1]:,.2f}<br>" +
                        "<b>Contracted:</b> $%{customdata[2]:,.2f}<extra></extra>"
                    )
                )

                fig_rate_disc.update_layout(
                    xaxis_ticksuffix="%",
                    xaxis_tickformat=".1f",
                    legend_title_text="Era",
                    margin=dict(l=0, r=10, t=30, b=0)
                )

                st.plotly_chart(fig_rate_disc, use_container_width=True)
        
    # =========================================================================
    # TAB: ANÁLISIS DE IMPACTO DE DUPLICADOS (DATA QUALITY)
    # =========================================================================
    with tab_duplicates:
        st.subheader("⚠️ Data Integrity & Duplicate Orders Impact Analysis")
        st.caption("Comparación entre el dataset original (con duplicados) y el dataset deduplicado de trabajo.")

        # 1. Obtener dataset bruto sin filtrar desde el session_state
        if 'ords_raw' in st.session_state:
            df_raw = st.session_state['ords_raw'].copy()
        else:
            df_raw = df_working.copy()  # Fallback en caso de no encontrar la variable
            
        df_raw['billed_amount'] = df_raw['qty_delivered'] * df_raw['billed_rate']
        df_raw['contracted_amount'] = df_raw['qty_delivered'] * df_raw['contracted_rate']
        df_raw['financial_discrepancy'] = df_raw['billed_amount'] - df_raw['contracted_amount']
        df_raw['volume_fulfillment_pct'] = (df_raw['qty_delivered'] / df_raw['qty_ordered'].replace(0, pd.NA)) * 100

        # 2. Identificar registros duplicados en el dataset bruto
        df_dups_all = df_raw[df_raw.duplicated(subset=['order_id'], keep=False)]
        
        # Dataset deduplicado de referencia
        df_clean = df_raw.drop_duplicates(subset=['order_id'], keep='first')

        # 3. Métricas del impacto de duplicidad
        duplicate_rows_count = len(df_raw) - len(df_clean)
        unique_affected_orders = df_dups_all['order_id'].nunique() if not df_dups_all.empty else 0

        # Inflación financiera y operacional si NO se eliminan
        raw_billed = df_raw['billed_amount'].sum() if 'billed_amount' in df_raw.columns else 0
        clean_billed = df_clean['billed_amount'].sum() if 'billed_amount' in df_clean.columns else 0
        phantom_revenue = raw_billed - clean_billed

        raw_ordered = df_raw['qty_ordered'].sum() if 'qty_ordered' in df_raw.columns else 0
        clean_ordered = df_clean['qty_ordered'].sum() if 'qty_ordered' in df_clean.columns else 0
        phantom_volume = raw_ordered - clean_ordered

        pct_overstated = (phantom_revenue / clean_billed * 100) if clean_billed > 0 else 0

        # --- BANNER DE RESUMEN EJECUTIVO (KPIs) ---
        d_col1, d_col2, d_col3, d_col4 = st.columns(4)

        with d_col1:
            st.metric(
                "Duplicate Rows Removed", 
                f"{duplicate_rows_count:,}", 
                delta=f"{unique_affected_orders:,} Orders Affected", 
                delta_color="normal"
            )
        with d_col2:
            st.metric(
                "Prevented Phantom Revenue", 
                f"${phantom_revenue:,.2f}", 
                delta=f"{pct_overstated:.2f}% Distortion Avoided", 
                delta_color="normal"
            )
        with d_col3:
            st.metric(
                "Prevented Phantom Volume", 
                f"{phantom_volume:,.0f} units", 
                delta="Overstated Demand Avoided", 
                delta_color="normal"
            )
        with d_col4:
            st.metric(
                "Clean Dataset Size", 
                f"{len(df_clean):,} rows", 
                delta=f"From {len(df_raw):,} Raw Rows", 
                delta_color="off"
            )

        st.divider()

        # --- DETALLE DEL IMPACTO Y TABLA DE DUPLICADOS DETECTADOS ---
        d_col_left, d_col_right = st.columns([1, 1])

        with d_col_left:
            st.markdown("**1. Business Impact: Raw Data vs Clean Data**")
            
            comp_data = {
                "Metric": ["Total Records", "Billed Revenue ($)", "Contracted Amount ($)", "Ordered Volume (Units)"],
                "Raw Data (ords_raw)": [
                    f"{len(df_raw):,}",
                    f"${raw_billed:,.2f}",
                    f"${df_raw['contracted_amount'].sum():,.2f}" if 'contracted_amount' in df_raw.columns else "$0.00",
                    f"{raw_ordered:,.0f}"
                ],
                "Clean Data (Working)": [
                    f"{len(df_clean):,}",
                    f"${clean_billed:,.2f}",
                    f"${df_clean['contracted_amount'].sum():,.2f}" if 'contracted_amount' in df_clean.columns else "$0.00",
                    f"{clean_ordered:,.0f}"
                ],
                "Risk / Overstatement": [
                    f"+{duplicate_rows_count:,} extra rows",
                    f"+${phantom_revenue:,.2f}",
                    f"+${(df_raw['contracted_amount'].sum() - df_clean['contracted_amount'].sum()):,.2f}" if 'contracted_amount' in df_raw.columns else "$0.00",
                    f"+{phantom_volume:,.0f} units"
                ]
            }
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

            st.error(
                "**Executive Takeaway:** If the team uses the undeduplicated file (`ords_raw`), "
                f"financial reports would overstate revenue by **${phantom_revenue:,.2f}** "
                f"({pct_overstated:.2f}%) and distort operational metrics."
            )

        with d_col_right:
            st.markdown("**2. Duplicate Records Detected in Raw File**")
            
            if not df_dups_all.empty:
                df_dups_sorted = df_dups_all.sort_values(by=['order_id']).reset_index(drop=True)
                cols_to_show = [c for c in ['order_id', 'customer_id', 'order_date', 'rate_category', 'qty_ordered', 'billed_amount', 'status', 'migration_flag'] if c in df_dups_sorted.columns]
                st.dataframe(df_dups_sorted[cols_to_show], use_container_width=True, height=320)
            else:
                st.success("No duplicate records were found in the raw dataset.")

    # =========================================================================
    # TAB 4: CUSTOMER SEGMENTATION (TOTAL $ AND PRE VS POST %)
    # =========================================================================
    with tab_segmentation:
        st.subheader("👥 Customer Segmentation & Performance Analysis")
        st.caption("Comparative analysis across Anchor Clients, Account Tiers, and Regions (Total Net Figures and PRE vs POST Normalized Shares).")

        req_cols = ['is_anchor', 'tier', 'region']
        has_segmentation = any(col in df_working.columns for col in req_cols)

        if not has_segmentation:
            st.info("No segmentation metadata (`is_anchor`, `tier`, `region`) was found in the loaded dataset.")
        else:
            # -----------------------------------------------------------------
            # SECTION A: TOTAL NET FIGURES ($) - BILLED VS CONTRACTED COMPARISON
            # -----------------------------------------------------------------
            st.markdown("## 💵 Overall Financial Overview (Billed vs Contracted)")
            
            # 1. Anchor Clients Total (Billed vs Contracted)
            if 'is_anchor' in df_working.columns:
                st.markdown("### 1. Anchor Clients vs Non-Anchor Clients")
                
                df_anchor_tot = (
                    df_working.groupby('is_anchor')
                    .agg(
                        billed_amount=('billed_amount', 'sum'),
                        contracted_amount=('contracted_amount', 'sum'),
                        financial_discrepancy=('financial_discrepancy', 'sum')
                    )
                    .reset_index()
                )
                df_anchor_tot['Segment'] = df_anchor_tot['is_anchor'].map({True: 'Anchor Client', False: 'Standard Client'}).fillna('Standard Client')

                # Melt para gráfico agrupado Billed vs Contracted
                df_anchor_melted = df_anchor_tot.melt(
                    id_vars=['Segment'],
                    value_vars=['billed_amount', 'contracted_amount'],
                    var_name='Amount_Type',
                    value_name='Amount'
                )
                df_anchor_melted['Amount_Type'] = df_anchor_melted['Amount_Type'].map({
                    'billed_amount': 'Billed Amount',
                    'contracted_amount': 'Contracted Amount'
                })

                anc_tot_col1, anc_tot_col2 = st.columns(2)

                with anc_tot_col1:
                    fig_anc_rev_tot = px.bar(
                        df_anchor_melted,
                        x='Segment',
                        y='Amount',
                        color='Amount_Type',
                        barmode='group',
                        labels={'Amount': 'Amount ($)', 'Segment': 'Segment', 'Amount_Type': 'Type'},
                        title="Billed vs Contracted Revenue by Anchor Status",
                        color_discrete_map={'Billed Amount': '#6366F1', 'Contracted Amount': '#10B981'},
                        template="plotly_white"
                    )
                    fig_anc_rev_tot.update_layout(yaxis_tickprefix="$")
                    st.plotly_chart(fig_anc_rev_tot, use_container_width=True)

                with anc_tot_col2:
                    fig_anc_disc_tot = px.bar(
                        df_anchor_tot,
                        x='Segment',
                        y='financial_discrepancy',
                        color='Segment',
                        labels={'financial_discrepancy': 'Financial Discrepancy ($)', 'Segment': 'Segment'},
                        title="Financial Leakage by Anchor Status",
                        color_discrete_map={'Standard Client': '#6366F1', 'Anchor Client': '#EF4444'},
                        template="plotly_white"
                    )
                    fig_anc_disc_tot.update_layout(yaxis_tickprefix="$", showlegend=False)
                    st.plotly_chart(fig_anc_disc_tot, use_container_width=True)

            # 2 & 3. Tier & Region Totals (Billed vs Contracted)
            tot_seg_col1, tot_seg_col2 = st.columns(2)

            with tot_seg_col1:
                if 'tier' in df_working.columns:
                    st.markdown("### 2. Revenue Comparison by Account Tier")
                    
                    df_tier_tot = (
                        df_working.groupby('tier')
                        .agg(
                            billed_amount=('billed_amount', 'sum'),
                            contracted_amount=('contracted_amount', 'sum')
                        )
                        .reset_index()
                    )

                    df_tier_melted = df_tier_tot.melt(
                        id_vars=['tier'],
                        value_vars=['billed_amount', 'contracted_amount'],
                        var_name='Amount_Type',
                        value_name='Amount'
                    )
                    df_tier_melted['Amount_Type'] = df_tier_melted['Amount_Type'].map({
                        'billed_amount': 'Billed Amount',
                        'contracted_amount': 'Contracted Amount'
                    })

                    fig_tier_tot = px.bar(
                        df_tier_melted,
                        x='tier',
                        y='Amount',
                        color='Amount_Type',
                        barmode='group',
                        text_auto='.3s',
                        labels={'Amount': 'Amount ($)', 'tier': 'Tier', 'Amount_Type': 'Type'},
                        title="Billed vs Contracted Amount ($) by Tier",
                        color_discrete_map={'Billed Amount': '#6366F1', 'Contracted Amount': '#10B981'},
                        template="plotly_white"
                    )
                    fig_tier_tot.update_layout(yaxis_tickprefix="$")
                    st.plotly_chart(fig_tier_tot, use_container_width=True)

            with tot_seg_col2:
                if 'region' in df_working.columns:
                    st.markdown("### 3. Financial Discrepancy by Region")
                    
                    df_region_tot = (
                        df_working.groupby('region')
                        .agg(
                            billed_amount=('billed_amount', 'sum'),
                            contracted_amount=('contracted_amount', 'sum'),
                            total_discrepancy=('financial_discrepancy', 'sum')
                        )
                        .reset_index()
                    )

                    fig_region_pie = px.pie(
                        df_region_tot,
                        names='region',
                        values='total_discrepancy',
                        title="Discrepancy Share (%) by Region",
                        hole=0.5,
                        template="plotly_white"
                    )
                    fig_region_pie.update_traces(textinfo='percent')
                    st.plotly_chart(fig_region_pie, use_container_width=True)

            # -----------------------------------------------------------------
            # SECTION B: PRE VS POST MIGRATION IMPACT ANALYSIS (NORMALIZED %)
            # -----------------------------------------------------------------
            st.markdown("## ⚖️ PRE vs POST Migration Impact (Normalized Share Comparison)")
            st.caption("Using normalized percentages (%) to eliminate volume bias caused by higher order counts in the PRE era.")

            # 1. Anchor Clients PRE vs POST (%)
            if 'is_anchor' in df_working.columns:
                st.markdown("### 1. Anchor Clients Normalized Comparison (PRE vs POST)")
                
                df_anchor_era = (
                    df_working.groupby(['is_anchor', era_col])
                    .agg(
                        total_billed=('billed_amount', 'sum'),
                        total_contracted=('contracted_amount', 'sum'),
                        total_discrepancy=('financial_discrepancy', 'sum')
                    )
                    .reset_index()
                )
                df_anchor_era['Segment'] = df_anchor_era['is_anchor'].map({True: 'Anchor Client', False: 'Standard Client'}).fillna('Standard Client')
                
                # Relative shares calculation
                df_anchor_era['revenue_share_pct'] = df_anchor_era.groupby(era_col)['total_billed'].transform(lambda x: (x / x.sum()) * 100)
                df_anchor_era['leakage_rate_pct'] = (df_anchor_era['total_discrepancy'] / df_anchor_era['total_contracted'].replace(0, pd.NA)) * 100

                anc_era_col1, anc_era_col2 = st.columns(2)

                with anc_era_col1:
                    fig_anc_rev_era = px.bar(
                        df_anchor_era,
                        x='Segment',
                        y='revenue_share_pct',
                        color=era_col,
                        barmode='group',
                        custom_data=['total_billed'],
                        labels={'revenue_share_pct': 'Revenue Share (%)', 'Segment': 'Segment', era_col: 'Era'},
                        title="Revenue Share (%) by Anchor Status (PRE vs POST)",
                        color_discrete_map={'PRE': '#1f77b4', 'POST': '#ff7f0e'},
                        template="plotly_white"
                    )
                    fig_anc_rev_era.update_traces(
                        hovertemplate="<b>Segment:</b> %{x}<br><b>Era:</b> %{fullData.name}<br><b>Share:</b> %{y:.2f}%<br><b>Billed ($):</b> $%{customdata[0]:,.2f}<extra></extra>"
                    )
                    fig_anc_rev_era.update_layout(yaxis_ticksuffix="%")
                    st.plotly_chart(fig_anc_rev_era, use_container_width=True)

                with anc_era_col2:
                    fig_anc_disc_era = px.bar(
                        df_anchor_era,
                        x='Segment',
                        y='leakage_rate_pct',
                        color=era_col,
                        barmode='group',
                        custom_data=['total_discrepancy'],
                        labels={'leakage_rate_pct': 'Leakage Rate (% of Contracted)', 'Segment': 'Segment', era_col: 'Era'},
                        title="Financial Leakage Rate (%) by Anchor Status",
                        color_discrete_map={'PRE': '#1f77b4', 'POST': '#ff7f0e'},
                        template="plotly_white"
                    )
                    fig_anc_disc_era.update_traces(
                        hovertemplate="<b>Segment:</b> %{x}<br><b>Era:</b> %{fullData.name}<br><b>Leakage Rate:</b> %{y:.2f}%<br><b>Discrepancy ($):</b> $%{customdata[0]:,.2f}<extra></extra>"
                    )
                    fig_anc_disc_era.update_layout(yaxis_ticksuffix="%")
                    st.plotly_chart(fig_anc_disc_era, use_container_width=True)

            # 2 & 3. Tier & Region PRE vs POST (%)
            era_seg_col1, era_seg_col2 = st.columns(2)

            with era_seg_col1:
                if 'tier' in df_working.columns:
                    st.markdown("### 2. Revenue Share (%) by Account Tier (PRE vs POST)")
                    df_tier_era = (
                        df_working.groupby(['tier', era_col])
                        .agg(billed_amount=('billed_amount', 'sum'))
                        .reset_index()
                    )

                    df_tier_era['revenue_share_pct'] = df_tier_era.groupby(era_col)['billed_amount'].transform(lambda x: (x / x.sum()) * 100)

                    fig_tier_era = px.bar(
                        df_tier_era,
                        x='tier',
                        y='revenue_share_pct',
                        color=era_col,
                        barmode='group',
                        custom_data=['billed_amount'],
                        labels={'revenue_share_pct': 'Revenue Share (%)', 'tier': 'Tier', era_col: 'Era'},
                        title="Revenue Share (%) by Account Tier",
                        color_discrete_map={'PRE': '#1f77b4', 'POST': '#ff7f0e'},
                        template="plotly_white"
                    )
                    fig_tier_era.update_traces(
                        hovertemplate="<b>Tier:</b> %{x}<br><b>Era:</b> %{fullData.name}<br><b>Share:</b> %{y:.2f}%<br><b>Billed ($):</b> $%{customdata[0]:,.2f}<extra></extra>"
                    )
                    fig_tier_era.update_layout(yaxis_ticksuffix="%")
                    st.plotly_chart(fig_tier_era, use_container_width=True)

            with era_seg_col2:
                if 'region' in df_working.columns:
                    st.markdown("### 3. Financial Discrepancy Share (%) by Region (PRE vs POST)")
                    df_region_era = (
                        df_working.groupby(['region', era_col])
                        .agg(discrepancy=('financial_discrepancy', 'sum'))
                        .reset_index()
                    )
                    df_region_era['discrepancy_share_pct'] = df_region_era.groupby(era_col)['discrepancy'].transform(lambda x: (x / x.sum()) * 100)

                    fig_region_era = px.bar(
                        df_region_era,
                        x='region',
                        y='discrepancy_share_pct',
                        color=era_col,
                        barmode='group',
                        custom_data=['discrepancy'],
                        labels={'discrepancy_share_pct': 'Discrepancy Share (%)', 'region': 'Region', era_col: 'Era'},
                        title="Discrepancy Share (%) by Region",
                        color_discrete_map={'PRE': '#1f77b4', 'POST': '#ff7f0e'},
                        template="plotly_white"
                    )
                    fig_region_era.update_traces(
                        hovertemplate="<b>Region:</b> %{x}<br><b>Era:</b> %{fullData.name}<br><b>Share:</b> %{y:.2f}%<br><b>Discrepancy ($):</b> $%{customdata[0]:,.2f}<extra></extra>"
                    )
                    fig_region_era.update_layout(yaxis_ticksuffix="%")
                    st.plotly_chart(fig_region_era, use_container_width=True)

            st.divider()

            # -----------------------------------------------------------------
            # SECTION C: DETAILED PERFORMANCE MATRIX
            # -----------------------------------------------------------------
            st.markdown("## 📋 Comprehensive Performance Matrix")
            
            group_cols = [c for c in ['tier', 'region', 'is_anchor', era_col] if c in df_working.columns]
            
            if group_cols:
                df_matrix = (
                    df_working.groupby(group_cols)
                    .agg(
                        Orders=('order_id', 'count'),
                        Total_Billed=('billed_amount', 'sum'),
                        Total_Contracted=('contracted_amount', 'sum'),
                        Net_Discrepancy=('financial_discrepancy', 'sum'),
                        Avg_Fulfillment=('volume_fulfillment_pct', 'mean')
                    )
                    .reset_index()
                )

                df_matrix['Leakage_Rate_Pct'] = (df_matrix['Net_Discrepancy'] / df_matrix['Total_Contracted'].replace(0, pd.NA)) * 100
                
                df_matrix['Leakage_Rate_Pct'] = df_matrix['Leakage_Rate_Pct'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")
                df_matrix['Total_Billed'] = df_matrix['Total_Billed'].apply(lambda x: f"${x:,.2f}")
                df_matrix['Total_Contracted'] = df_matrix['Total_Contracted'].apply(lambda x: f"${x:,.2f}")
                df_matrix['Net_Discrepancy'] = df_matrix['Net_Discrepancy'].apply(lambda x: f"${x:,.2f}")
                df_matrix['Avg_Fulfillment'] = df_matrix['Avg_Fulfillment'].apply(lambda x: f"{x:.1f}%")

                df_matrix = df_matrix.rename(columns={
                    era_col: 'Era',
                    'is_anchor': 'Is Anchor',
                    'tier': 'Tier',
                    'region': 'Region',
                    'Leakage_Rate_Pct': 'Leakage Rate (%)',
                    'Avg_Fulfillment': 'Fulfillment Rate (%)'
                })

                st.dataframe(df_matrix, use_container_width=True, hide_index=True)

    st.divider()

    # =========================================================================
    # ACCIONES ESTRATÉGICAS
    # =========================================================================
    st.subheader("Action Items")
    rec1, rec2, rec3 = st.columns(3)
    with rec1:
        st.success("**1. Rate Alignment**\nFix billed_rate calculations where billed_rate != contracted_rate.")
    with rec2:
        st.success("**2. Delivery Reconciliation**\nAudit order statuses (DELIVERED vs PARTIAL) against physical records.")
    with rec3:
        st.success("**3. Pre-Billing Validation**\nSet up automated alerts when billed_rate diverges from contracted_rate.")

def app():
    """Función de entrada para llamadas dinámicas desde app.py"""
    df_orders = st.session_state.get('ords_clean').query("~qty_ordered.isna()")
    df_accounts = st.session_state.get('accs_clean')

    render_finops_page(df_orders, df_accounts)