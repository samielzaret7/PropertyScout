"""
PropertyScout — Market Analytics
==================================
Charts and statistical breakdowns for market analysis.
All charts respond to sidebar filters including the global year filter.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_base_types, load_properties, load_regions
from utils.formatting import (
    LISTING_STATUS_LABELS,
    REGION_COLORS,
    REGION_LABELS,
    fmt_price,
)
from utils.sidebar import render_year_filter

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Analytics — PropertyScout PR",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("📊 Analytics Filters")

all_regions = load_regions()
selected_regions = st.sidebar.multiselect(
    "Region",
    options=all_regions,
    default=[],
    format_func=lambda r: REGION_LABELS.get(r, r.title()),
    placeholder="All regions",
)
regions_key = tuple(sorted(selected_regions))

all_types = load_base_types()
selected_types = st.sidebar.multiselect(
    "Property Type",
    options=all_types,
    default=[],
    placeholder="All types",
)

price_min, price_max = st.sidebar.slider(
    "Price Range (USD)",
    min_value=0,
    max_value=10_000_000,
    value=(0, 5_000_000),
    step=25_000,
    format="$%d",
)

log_scale = st.sidebar.checkbox("Log price scale on distributions", value=True)

# Global year filter
selected_year = render_year_filter()

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
with st.spinner("Loading analytics data…"):
    df = load_properties(
        regions=regions_key,
        base_types=tuple(sorted(selected_types)),
        price_min=float(price_min),
        price_max=float(price_max),
        year=selected_year,
    )

year_label = str(selected_year) if selected_year else "All Years"
st.title(f"Market Analytics — {year_label}")
st.caption(f"Analysing **{len(df):,}** listings matching the selected filters.")

if df.empty:
    st.info("No data for the selected filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Row 1: Price distribution + Box plots by type
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Price Distribution by Region")
    fig_hist = px.histogram(
        df,
        x="price",
        color="region_clean",
        nbins=60,
        log_x=log_scale,
        barmode="overlay",
        opacity=0.65,
        color_discrete_map=REGION_COLORS,
        labels={"price": "Price (USD)", "region_clean": "Region"},
    )
    fig_hist.update_layout(legend_title="Region", margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    st.subheader("Price Range by Property Type")
    fig_box = px.box(
        df,
        x="base_type",
        y="price",
        log_y=log_scale,
        color="base_type",
        color_discrete_sequence=px.colors.qualitative.Safe,
        labels={"price": "Price (USD)", "base_type": "Type"},
        points=False,
    )
    fig_box.update_layout(
        showlegend=False,
        xaxis_tickangle=-30,
        margin=dict(l=0, r=0, t=20, b=60),
    )
    st.plotly_chart(fig_box, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Median price by pueblo + Listings over time
# ---------------------------------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    st.subheader("Median Price — Top 20 Municipalities by Volume")
    pueblo_stats = (
        df.groupby("pueblo")
        .agg(count=("property_id", "count"), median_price=("price", "median"))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(20)
        .sort_values("median_price", ascending=True)
    )
    fig_pueblo = px.bar(
        pueblo_stats,
        x="median_price",
        y="pueblo",
        orientation="h",
        color="median_price",
        color_continuous_scale="Greens",
        text=pueblo_stats["median_price"].apply(fmt_price),
        labels={"median_price": "Median Price (USD)", "pueblo": "Municipality"},
    )
    fig_pueblo.update_traces(textposition="outside")
    fig_pueblo.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=60, t=20, b=0),
    )
    st.plotly_chart(fig_pueblo, use_container_width=True)

with col4:
    st.subheader("New Listings Over Time (by Week)")
    if "last_seen" in df.columns and df["last_seen"].notna().any():
        time_df = df.copy()
        time_df["last_seen"] = pd.to_datetime(time_df["last_seen"])
        time_df["week"] = time_df["last_seen"].dt.to_period("W").apply(lambda r: r.start_time)
        weekly = (
            time_df.groupby(["week", "region_clean"])
            .size()
            .reset_index(name="count")
        )
        fig_time = px.line(
            weekly,
            x="week",
            y="count",
            color="region_clean",
            color_discrete_map=REGION_COLORS,
            labels={"week": "Week", "count": "Listings Seen", "region_clean": "Region"},
            markers=True,
        )
        fig_time.update_layout(legend_title="Region", margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No date data available for this filter.")

# ---------------------------------------------------------------------------
# Row 3: Price drops analysis + Listing status by region
# ---------------------------------------------------------------------------
col5, col6 = st.columns(2)

with col5:
    st.subheader("💰 Price Drop Analysis")
    drops_df = df[df["price_changed"] == True].copy()
    if not drops_df.empty and drops_df["price_change_pct"].notna().any():
        fig_drops = px.histogram(
            drops_df,
            x="price_change_pct",
            color="base_type",
            nbins=30,
            labels={"price_change_pct": "Price Change (%)", "base_type": "Type"},
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_drops.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.5)
        fig_drops.update_layout(
            legend_title="Type",
            margin=dict(l=0, r=0, t=20, b=0),
            bargap=0.1,
        )
        st.plotly_chart(fig_drops, use_container_width=True)
        st.caption(
            f"{len(drops_df):,} listings with price changes · "
            f"Avg change: {drops_df['price_change_pct'].mean():.1f}%"
        )
    else:
        st.info("No price drop data for the selected filters.")

with col6:
    st.subheader("Listing Status by Region")
    status_region = (
        df.groupby(["region_clean", "listing_status"])
        .size()
        .reset_index(name="count")
    )
    status_region["status_label"] = status_region["listing_status"].map(LISTING_STATUS_LABELS)
    fig_status = px.bar(
        status_region,
        x="region_clean",
        y="count",
        color="status_label",
        barmode="group",
        color_discrete_sequence=["#2E7D32", "#81C784", "#E65100"],
        labels={"region_clean": "Region", "count": "Listings", "status_label": "Status"},
    )
    fig_status.update_layout(legend_title="Status", margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_status, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 4: Price vs bedrooms scatter + Price statistics table
# ---------------------------------------------------------------------------
col7, col8 = st.columns(2)

with col7:
    st.subheader("Price vs Bedrooms")
    scatter_df = df[df["bedrooms_int"] > 0].copy()
    scatter_df["bedrooms_label"] = scatter_df["bedrooms_int"].apply(
        lambda x: "6+" if x >= 6 else str(int(x))
    )
    fig_scatter = px.strip(
        scatter_df,
        x="bedrooms_label",
        y="price",
        color="region_clean",
        log_y=log_scale,
        color_discrete_map=REGION_COLORS,
        labels={"price": "Price (USD)", "bedrooms_label": "Bedrooms", "region_clean": "Region"},
        hover_data=["title", "pueblo", "base_type"],
    )
    fig_scatter.update_layout(legend_title="Region", margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig_scatter, use_container_width=True)

with col8:
    st.subheader("Price Statistics by Region")
    region_stats = (
        df.groupby("region_clean")["price"]
        .describe(percentiles=[0.25, 0.5, 0.75])
        .reset_index()
    )
    for c in ["min", "25%", "50%", "75%", "max", "mean"]:
        if c in region_stats.columns:
            region_stats[c] = region_stats[c].apply(fmt_price)
    region_stats = region_stats.rename(columns={
        "region_clean": "Region", "count": "# Listings",
        "mean": "Mean", "min": "Min", "50%": "Median", "max": "Max",
    })
    display_cols = [c for c in ["Region", "# Listings", "Min", "25%", "Median", "75%", "Max", "Mean"] if c in region_stats.columns]
    st.dataframe(region_stats[display_cols], use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Row 5: Neighbourhood type distribution
# ---------------------------------------------------------------------------
st.subheader("Neighbourhood Type Distribution")
prefix_counts = (
    df.groupby("barrio_prefix").size().reset_index(name="count").sort_values("count", ascending=False)
)
fig_prefix = px.bar(
    prefix_counts,
    x="barrio_prefix",
    y="count",
    color="count",
    color_continuous_scale="Greens",
    text="count",
    labels={"barrio_prefix": "Neighbourhood Type", "count": "Listings"},
)
fig_prefix.update_traces(textposition="outside")
fig_prefix.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=0, t=20, b=0))
st.plotly_chart(fig_prefix, use_container_width=True)

st.markdown("---")
st.caption("All prices in USD · Data refreshes hourly · Built with Streamlit + Supabase")
