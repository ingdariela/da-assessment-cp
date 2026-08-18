import streamlit as st
import services.data_service as data_service


def render_dataset_audit_section_metrics(titles: list, raw_dfs: list, clean_dfs: list):
    """Renders standardized data quality metrics with total and pre/post migration splits."""

    for i in range(len(titles)):
        title, raw_df, clean_df = titles[i], raw_dfs[i], clean_dfs[i]

        st.subheader(f"{title} Deduplication Overview")

        # Calculates total metrics first
        tot_raw = len(raw_df)
        tot_clean = len(clean_df)
        tot_removed = tot_raw - tot_clean
        tot_eff = (tot_clean / tot_raw * 100) if tot_raw > 0 else 0

        # Check if the dataset has 'migration_flag' (e.g., Orders)
        if "migration_flag" in raw_df.columns:
            # 1. Overall Total Metrics
            st.markdown("**Total Orders (Combined)**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Original Records", f"{tot_raw:,}")
            col2.metric(
                "Total Clean Records",
                f"{tot_clean:,}",
                delta=f"-{tot_removed:,} duplicates" if tot_removed > 0 else "0 duplicates",
                delta_color="inverse",
            )
            col3.metric("Overall Efficiency", f"{tot_eff:.2f}%")

            # 2. Filter Pre / Post Migration
            pre_raw = raw_df[raw_df["migration_flag"].astype(str).str.upper().str.contains("PRE")]
            post_raw = raw_df[raw_df["migration_flag"].astype(str).str.upper().str.contains("POST")]

            pre_clean = clean_df[clean_df["migration_flag"].astype(str).str.upper().str.contains("PRE")]
            post_clean = clean_df[clean_df["migration_flag"].astype(str).str.upper().str.contains("POST")]

            # Pre-Migration calculations
            pre_raw_len, pre_clean_len = len(pre_raw), len(pre_clean)
            pre_removed = pre_raw_len - pre_clean_len
            pre_eff = (pre_clean_len / pre_raw_len * 100) if pre_raw_len > 0 else 0

            # Post-Migration calculations
            post_raw_len, post_clean_len = len(post_raw), len(post_clean)
            post_removed = post_raw_len - post_clean_len
            post_eff = (post_clean_len / post_raw_len * 100) if post_raw_len > 0 else 0

            # 3. Breakdown Rows (Pre and Post)
            st.caption("Migration Phase Breakdown")
            
            col_pre, col_post = st.columns(2)

            with col_pre:
                st.markdown("**Pre-Migration Orders**")
                st.metric("Original Records", f"{pre_raw_len:,}")
                st.metric(
                    "Clean Records",
                    f"{pre_clean_len:,}",
                    delta=f"-{pre_removed:,} duplicates" if pre_removed > 0 else "0 duplicates",
                    delta_color="inverse",
                )
                st.metric("Efficiency", f"{pre_eff:.2f}%")
                
                df = data_service.get_orders_with_conflict_details(raw_df.query("migration_flag == 'PRE'"), 'order_id')
                
                st.dataframe(df, height=250, use_container_width=True, hide_index=True)
                st.write(df[["diff_billed_rate", "diff_qty_ordered", "diff_qty_delivered"]].describe())

            with col_post:
                st.markdown("**Post-Migration Orders**")
                st.metric("Original Records", f"{post_raw_len:,}")
                st.metric(
                    "Clean Records",
                    f"{post_clean_len:,}",
                    delta=f"-{post_removed:,} duplicates" if post_removed > 0 else "0 duplicates",
                    delta_color="inverse",
                )
                st.metric("Efficiency", f"{post_eff:.2f}%")
                
                df = data_service.get_orders_with_conflict_details(raw_df.query("migration_flag == 'POST'"), 'order_id')
                                
                st.dataframe(df, height=250, use_container_width=True, hide_index=True)
                st.write(df[["diff_billed_rate", "diff_qty_ordered", "diff_qty_delivered"]].describe())

        else:
            # Standard metrics layout (e.g., Accounts)
            col1, col2, col3 = st.columns(3)
            col1.metric("Original Records", f"{tot_raw:,}")
            col2.metric(
                "Clean Records",
                f"{tot_clean:,}",
                delta=f"-{tot_removed:,} duplicates" if tot_removed > 0 else "0 duplicates",
                delta_color="inverse",
            )
            col3.metric("Deduplication Efficiency", f"{tot_eff:.2f}%")

        if i < len(titles) - 1:
            st.divider()
             
def render_dataset_audit_section_tabs(
    titles: list,
    raw_dfs,
    clean_dfs,
    plot_service,
):
    """Renders a standardized data quality & profiling block for any dataset."""

    # 2. Tabs view (Preview, Profile Table, Raw State)
    tab_overview, tab_profile, tab_clean, tab_raw = st.tabs(
        ["Deduplication overview", "Data Profile & Quality", "Clean State Data", "Raw State Data"]
    )
    
    with tab_overview:
    
        render_dataset_audit_section_metrics(
            titles,
            raw_dfs,
            clean_dfs
        )
    
    with tab_profile:
        st.subheader(f"{titles[0]} Profile Summary")
        plot_service.render_data_profile_table(clean_dfs[0])
        
        st.subheader(f"{titles[1]} Profile Summary")
        col_profile_pre, col_profile_post = st.columns(2)
        with col_profile_pre:
            st.caption("Pre Migration")
            plot_service.render_data_profile_table(clean_dfs[1].query("migration_flag == 'PRE'").sort_values("order_date"))
        
        with col_profile_post:
            st.caption("Post Migration")
            plot_service.render_data_profile_table(clean_dfs[1].query("migration_flag == 'POST'").sort_values("order_date"))

    with tab_clean:
        st.subheader(f"{titles[0]} Clean Dataset")
        st.dataframe(clean_dfs[0], height=250, use_container_width=True, hide_index=True)
        
        st.subheader(f"{titles[1]} Clean Dataset")
        col_clean_pre, col_clean_post = st.columns(2)
        with col_clean_pre:
            st.caption("Pre Migration")
            st.dataframe(clean_dfs[1].query("migration_flag == 'PRE'").sort_values("order_date"), height=250, use_container_width=True, hide_index=True)
        
        with col_clean_post:
            st.caption("Post Migration")
            st.dataframe(clean_dfs[1].query("migration_flag == 'POST'").sort_values("order_date"), height=250, use_container_width=True, hide_index=True)
            
    with tab_raw:
        st.subheader(f"{titles[0]} Raw Dataset")
        st.dataframe(raw_dfs[0], height=250, use_container_width=True, hide_index=True)
        
        st.subheader(f"{titles[1]} Raw Dataset")
        
        col_raw_pre, col_raw_post = st.columns(2)
        with col_raw_pre:
            st.caption("Pre Migration")
            st.dataframe(raw_dfs[1].query("migration_flag == 'PRE'").sort_values("order_date"), height=250, use_container_width=True, hide_index=True)
        
        with col_raw_post:
            st.caption("Post Migration")
            st.dataframe(raw_dfs[1].query("migration_flag == 'POST'").sort_values("order_date"), height=250, use_container_width=True, hide_index=True)
    

