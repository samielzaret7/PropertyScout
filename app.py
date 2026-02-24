"""
PropertyScout — Home / KPI Overview
====================================
Entry point for the Streamlit multi-page app.
Shows market-wide KPIs and summary charts, with region and year filters in the sidebar.
"""
import plotly.express as px
import streamlit as st

from utils.data_loader import (
    load_counts_by_region,
    load_counts_by_type,
    load_kpi_summary,
    load_regions,
    load_status_breakdown,
    load_top_brokers,
)
from utils.formatting import (
    LISTING_STATUS_LABELS,
    REGION_COLORS,
    fmt_price,
    fmt_pct,
)
from utils.sidebar import render_broker_filter, render_year_filter

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PropertyScout PR",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🏡 PropertyScout PR")
st.sidebar.subheader("Filter by Region")

all_regions = load_regions()
selected_regions = st.sidebar.multiselect(
    "Region",
    options=all_regions,
    default=[],
    placeholder="All regions",
)
regions_key = tuple(sorted(selected_regions))

brokers_key = render_broker_filter()

# Global year filter (shared across all pages via session_state)
selected_year = render_year_filter()

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh data", help="Clear cache and reload from Supabase"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
year_label = str(selected_year) if selected_year else "All Years"
st.title(f"Puerto Rico Real Estate — Market Overview ({year_label})")
st.caption(
    "Data sourced from clasificadosonline.com · Refreshed every hour · "
    "Use the **Search** and **Analytics** pages for detailed exploration."
)

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
with st.spinner("Loading market data…"):
    kpis = load_kpi_summary(regions=regions_key, year=selected_year, brokers=brokers_key)

if not kpis:
    st.warning("No listings found for the selected filters.")
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Listings", f"{kpis['total']:,}")
col2.metric("Median Price", fmt_price(kpis["median_price"]))
col3.metric("Average Price", fmt_price(kpis["avg_price"]))
col4.metric("Under Contract", fmt_pct(kpis["pct_optioned"]))
col5.metric("💰 Price Drops", f"{kpis['price_drops']:,}", help="Listings where a price reduction was detected")

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1: Count by region + Count by type
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Listings by Region")
    df_region = load_counts_by_region(regions=regions_key, year=selected_year, brokers=brokers_key)
    if not df_region.empty:
        fig = px.bar(
            df_region.sort_values("count", ascending=True),
            x="count",
            y="region_clean",
            orientation="h",
            color="region_clean",
            color_discrete_map=REGION_COLORS,
            labels={"count": "Listings", "region_clean": "Region"},
            text="count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(l=0, r=20, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Listings by Property Type")
    df_type = load_counts_by_type(regions=regions_key, year=selected_year, brokers=brokers_key)
    if not df_type.empty:
        fig2 = px.bar(
            df_type.sort_values("count", ascending=True),
            x="count",
            y="base_type",
            orientation="h",
            color="count",
            color_continuous_scale="Greens",
            labels={"count": "Listings", "base_type": "Type"},
            text="count",
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=0, r=20, t=20, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Listing status donut + Top brokers table
# ---------------------------------------------------------------------------
col_left2, col_right2 = st.columns([1, 2])

with col_left2:
    st.subheader("Listing Status")
    df_status = load_status_breakdown(regions=regions_key, year=selected_year, brokers=brokers_key)
    if not df_status.empty:
        df_status["label"] = df_status["listing_status"].map(LISTING_STATUS_LABELS)
        fig3 = px.pie(
            df_status,
            values="count",
            names="label",
            hole=0.45,
            color_discrete_sequence=["#2E7D32", "#81C784", "#C8E6C9"],
        )
        fig3.update_traces(textposition="inside", textinfo="percent+label")
        fig3.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig3, use_container_width=True)

with col_right2:
    st.subheader("Top 10 Most Active Brokers")
    df_brokers = load_top_brokers(regions=regions_key, year=selected_year, brokers=brokers_key)
    if not df_brokers.empty:
        df_brokers.columns = ["Broker", "Listings"]
        df_brokers = df_brokers.reset_index(drop=True)
        df_brokers.index += 1
        st.dataframe(df_brokers, use_container_width=True, height=350)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Navigate to **Search** to filter properties · **Analytics** for market charts · "
    "Built with [Streamlit](https://streamlit.io) + [Supabase](https://supabase.com)"
)
