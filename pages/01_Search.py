"""
PropertyScout — Property Search
================================
Filter-driven property browser backed by the `properties_enriched` Supabase view.
Supports table view (with thumbnails) and card-grid view.
"""
import pandas as pd
import streamlit as st

from utils.data_loader import (
    load_barrio_prefixes,
    load_base_types,
    load_properties,
    load_pueblos,
    load_regions,
)
from utils.formatting import (
    BATHROOMS_OPTIONS,
    BEDROOMS_OPTIONS,
    LISTING_STATUS_LABELS,
    REGION_LABELS,
    beds_label,
    fmt_price,
)
from utils.sidebar import render_broker_filter, render_price_filter, render_year_filter

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Search — PropertyScout PR",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("🔍 Search Filters")

all_regions = load_regions()
selected_regions = st.sidebar.multiselect(
    "Region",
    options=all_regions,
    default=[],
    format_func=lambda r: REGION_LABELS.get(r, r.title()),
    placeholder="All regions",
)
regions_key = tuple(sorted(selected_regions))
brokers_key = render_broker_filter()

# Dynamic municipality list filtered by selected regions
all_pueblos = load_pueblos(regions=regions_key if regions_key else None)
selected_pueblos = st.sidebar.multiselect(
    "Municipality (Pueblo)",
    options=all_pueblos,
    default=[],
    placeholder="All municipalities",
)

st.sidebar.markdown("---")

all_types = load_base_types()
selected_types = st.sidebar.multiselect(
    "Property Type",
    options=all_types,
    default=[],
    placeholder="All types",
)

selected_statuses = st.sidebar.multiselect(
    "Listing Status",
    options=list(LISTING_STATUS_LABELS.keys()),
    default=[],
    format_func=lambda s: LISTING_STATUS_LABELS[s],
    placeholder="All statuses",
)

st.sidebar.markdown("---")

price_min, price_max = render_price_filter(page="search")

st.sidebar.markdown("---")

min_beds_idx = st.sidebar.selectbox(
    "Min Bedrooms",
    options=range(len(BEDROOMS_OPTIONS)),
    format_func=lambda i: BEDROOMS_OPTIONS[i][1],
    index=0,
)
min_beds = BEDROOMS_OPTIONS[min_beds_idx][0]

min_baths_idx = st.sidebar.selectbox(
    "Min Bathrooms",
    options=range(len(BATHROOMS_OPTIONS)),
    format_func=lambda i: BATHROOMS_OPTIONS[i][1],
    index=0,
)
min_baths = BATHROOMS_OPTIONS[min_baths_idx][0]

st.sidebar.markdown("---")

all_prefixes = load_barrio_prefixes()
selected_prefixes = st.sidebar.multiselect(
    "Neighbourhood Type",
    options=all_prefixes,
    default=[],
    placeholder="All types",
)

st.sidebar.markdown("---")

hide_optioned = st.sidebar.checkbox("Hide properties under contract", value=False)
fsbo_only = st.sidebar.checkbox("FSBO only (No broker)", value=False)
price_drops_only = st.sidebar.checkbox("💰 Price drops only", value=False)
price_increases_only = st.sidebar.checkbox("📈 Price increases only", value=False)

# Global year filter
selected_year = render_year_filter()

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
with st.spinner("Querying listings…"):
    df = load_properties(
        regions=regions_key,
        base_types=tuple(sorted(selected_types)),
        listing_statuses=tuple(sorted(selected_statuses)),
        price_min=float(price_min),
        price_max=float(price_max),
        min_bedrooms=min_beds,
        min_bathrooms=min_baths,
        pueblos=tuple(sorted(selected_pueblos)),
        barrio_prefixes=tuple(sorted(selected_prefixes)),
        hide_optioned=hide_optioned,
        fsbo_only=fsbo_only,
        year=selected_year,
        brokers=brokers_key,
    )

# Client-side price-change filters
if (price_drops_only or price_increases_only) and not df.empty:
    if price_drops_only and price_increases_only:
        # Both checked → show any price change
        df = df[df["price_changed"] == True].reset_index(drop=True)
    elif price_drops_only:
        df = df[(df["price_changed"] == True) & (df["price_change_pct"] < 0)].reset_index(drop=True)
    else:
        df = df[(df["price_changed"] == True) & (df["price_change_pct"] > 0)].reset_index(drop=True)

# ---------------------------------------------------------------------------
# Header + view toggle
# ---------------------------------------------------------------------------
st.title("Property Search")

# Persist view mode across page navigations; default = Cards
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "Cards"

col_count, col_cards, col_table = st.columns([4, 1, 1])
with col_count:
    year_label = str(selected_year) if selected_year else "All Years"
    st.markdown(f"**{len(df):,} listing{'s' if len(df) != 1 else ''} found** · {year_label}")
with col_cards:
    if st.button(
        "🃏  Cards",
        use_container_width=True,
        type="primary" if st.session_state["view_mode"] == "Cards" else "secondary",
    ):
        st.session_state["view_mode"] = "Cards"
        st.rerun()
with col_table:
    if st.button(
        "📋  Table",
        use_container_width=True,
        type="primary" if st.session_state["view_mode"] == "Table" else "secondary",
    ):
        st.session_state["view_mode"] = "Table"
        st.rerun()

view_mode = st.session_state["view_mode"]

if df.empty:
    st.info("No listings match the selected filters. Try broadening your search.")
    st.stop()

# ---------------------------------------------------------------------------
# Sort control
# ---------------------------------------------------------------------------
SORT_OPTIONS = {
    "last_seen": "Last Seen (newest first)",
    "price": "Price",
    "first_seen": "First Seen",
    "times_seen": "Times Seen",
    "bedrooms_int": "Bedrooms",
    "bathrooms_int": "Bathrooms",
    "pueblo": "Municipality",
    "base_type": "Type",
}

sort_col, sort_dir_col = st.columns([2, 1])
with sort_col:
    sort_by = st.selectbox(
        "Sort by",
        options=list(SORT_OPTIONS.keys()),
        format_func=lambda c: SORT_OPTIONS[c],
        index=0,  # default: last_seen
    )
with sort_dir_col:
    # Default: descending for dates/price, ascending for text
    default_desc = sort_by in ("last_seen", "first_seen", "price", "times_seen")
    ascending = st.selectbox(
        "Order",
        options=[False, True],
        format_func=lambda b: "Low → High" if b else "High → Low",
        index=0 if default_desc else 1,
    )

df = df.sort_values(sort_by, ascending=ascending, na_position="last").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
PAGE_SIZE = 50
total_pages = max(1, -(-len(df) // PAGE_SIZE))
page = st.number_input(
    f"Page (1–{total_pages})",
    min_value=1,
    max_value=total_pages,
    value=1,
    step=1,
)
page_df = df.iloc[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

# ---------------------------------------------------------------------------
# Table view (with thumbnail images)
# ---------------------------------------------------------------------------
if view_mode == "Table":
    display = page_df[[
        "piclink", "title", "price", "base_type", "listing_status",
        "pueblo", "region_clean", "bedrooms_int", "bathrooms_int",
        "price_changed", "price_change_pct",
        "first_seen", "last_seen", "days_tracked", "broker", "link",
    ]].copy()

    display["price_fmt"] = display["price"].apply(fmt_price)
    display["listing_status"] = display["listing_status"].map(LISTING_STATUS_LABELS)
    display["bedrooms_int"] = display["bedrooms_int"].apply(beds_label)
    display["bathrooms_int"] = display["bathrooms_int"].apply(beds_label)
    # Show direction-aware label
    def _price_change_label(row) -> str:
        if not row["price_changed"]:
            return ""
        pct = row.get("price_change_pct")
        if pct is None:
            return "Changed"
        return f"💰 -{abs(pct):.1f}%" if pct < 0 else f"📈 +{pct:.1f}%"

    display["price_changed"] = display.apply(_price_change_label, axis=1)
    display = display.drop(columns=["price_change_pct"])

    display = display.rename(columns={
        "piclink": "Photo",
        "title": "Title",
        "price_fmt": "Price",
        "base_type": "Type",
        "listing_status": "Status",
        "pueblo": "Pueblo",
        "region_clean": "Region",
        "bedrooms_int": "Beds",
        "bathrooms_int": "Baths",
        "price_changed": "Drop",
        "first_seen": "First Seen",
        "last_seen": "Last Seen",
        "days_tracked": "Days on Market",
        "broker": "Broker",
        "link": "Link",
    })
    # Drop the original numeric price column, keep the formatted "Price" one
    display = display.drop(columns=["price"])

    st.dataframe(
        display,
        use_container_width=True,
        height=650,
        column_config={
            "Photo": st.column_config.ImageColumn("Photo", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Link": st.column_config.LinkColumn("Link", display_text="View →"),
            "First Seen": st.column_config.DateColumn("First Seen", format="MMM D, YYYY"),
            "Last Seen": st.column_config.DateColumn("Last Seen", format="MMM D, YYYY"),
            "Days on Market": st.column_config.NumberColumn("Days on Market", format="%d d"),
        },
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Card grid view (3 columns, images prominently displayed)
# ---------------------------------------------------------------------------
else:
    COLS = 3
    rows = [page_df.iloc[i : i + COLS] for i in range(0, len(page_df), COLS)]

    for row in rows:
        cols = st.columns(COLS)
        for col, (_, prop) in zip(cols, row.iterrows()):
            with col:
                with st.container(border=True):
                    # Property image — use plain HTML <img> so CSS width:100%
                    # fills the column immediately on first render (st.image with
                    # use_container_width=True can render at native size until the
                    # first JS reflow, causing the "tiny then normal" flicker).
                    if prop.get("piclink"):
                        st.markdown(
                            f'<img src="{prop["piclink"]}" '
                            f'style="width:100%;height:180px;object-fit:cover;'
                            f'border-radius:6px;margin-bottom:4px;" />',
                            unsafe_allow_html=True,
                        )

                    # Price change badge (drop or increase)
                    if prop.get("price_changed") and prop.get("previous_price"):
                        pct = prop.get("price_change_pct")
                        is_drop = pct is not None and pct < 0
                        pct_str = f" ({pct:+.1f}%)" if pct is not None else ""
                        badge_color = "#2E7D32" if is_drop else "#1565C0"
                        badge_label = "💰 PRICE DROP" if is_drop else "📈 PRICE INCREASE"
                        prev = fmt_price(prop["previous_price"]).replace("$", "&#36;")
                        curr = fmt_price(prop["price"]).replace("$", "&#36;")
                        st.markdown(
                            f"<span style='background:{badge_color};color:white;padding:2px 6px;"
                            f"border-radius:4px;font-size:0.75rem'>{badge_label}{pct_str}</span>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<s style='color:gray'>{prev}</s>"
                            f"&nbsp;&nbsp;→&nbsp;&nbsp;<strong>{curr}</strong>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"### {fmt_price(prop['price']).replace('$', '&#36;')}", unsafe_allow_html=True)

                    # Title (truncated)
                    title = str(prop.get("title", ""))
                    st.markdown(f"**{title[:55]}{'…' if len(title) > 55 else ''}**")

                    # Type + status badge
                    status = LISTING_STATUS_LABELS.get(prop.get("listing_status", "standard"), "")
                    type_str = prop.get("base_type", "")
                    badge = f"  `{status}`" if status != "Standard" else ""
                    st.caption(f"{type_str}{badge}")

                    # Beds / baths / pueblo
                    beds = beds_label(prop.get("bedrooms_int"))
                    baths = beds_label(prop.get("bathrooms_int"))
                    parts = []
                    if beds != "—" or baths != "—":
                        parts.append(f"{beds} bd / {baths} ba")
                    if prop.get("pueblo"):
                        parts.append(prop["pueblo"])
                    if parts:
                        st.caption(" · ".join(parts))

                    # Broker
                    if prop.get("is_fsbo"):
                        st.caption("👤 FSBO (No broker)")
                    elif prop.get("broker"):
                        st.caption(f"🏢 {prop['broker']}")

                    # Market timing
                    first = prop.get("first_seen")
                    last = prop.get("last_seen")
                    days = prop.get("days_tracked")
                    timing_lines = []
                    if first:
                        timing_lines.append(f"🗓 First seen: &nbsp;<b>{first}</b>")
                    if last:
                        timing_lines.append(f"🕒 Last seen: &nbsp;&nbsp;<b>{last}</b>")
                    if days is not None:
                        timing_lines.append(f"📅 Days on market: <b>{int(days)}d</b>")
                    if timing_lines:
                        st.markdown(
                            "<small style='color:gray;line-height:2'>"
                            + "<br>".join(timing_lines)
                            + "</small>",
                            unsafe_allow_html=True,
                        )

                    if prop.get("link"):
                        st.link_button("View listing →", prop["link"])

st.markdown("---")
st.caption(f"Showing {len(page_df)} of {len(df)} results · Page {page}/{total_pages}")
