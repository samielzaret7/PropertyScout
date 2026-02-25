"""
Shared sidebar components rendered on every page.
Stores selections in st.session_state so values persist across page navigation.
"""
from __future__ import annotations

import streamlit as st

from utils.data_loader import load_available_years, load_brokers, load_max_price

_DEFAULT_YEAR = 2026


def render_year_filter() -> int | None:
    """
    Render the global 'Last Seen Year' filter in the sidebar.
    Returns the selected year as an int, or None if 'All years' is chosen.
    Persists the selection in st.session_state['selected_year'].
    """
    years = load_available_years()

    # Fallback if DB has no data yet
    if not years:
        years = [_DEFAULT_YEAR]

    options = ["All years"] + [str(y) for y in years]

    # Determine default index: prefer _DEFAULT_YEAR, else first year
    default_label = str(_DEFAULT_YEAR) if _DEFAULT_YEAR in years else str(years[0])
    default_idx = options.index(default_label) if default_label in options else 1

    # Restore previous selection if navigating back
    saved = st.session_state.get("selected_year_label")
    if saved and saved in options:
        default_idx = options.index(saved)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Global Filter")
    selected_label = st.sidebar.selectbox(
        "Last Seen Year",
        options=options,
        index=default_idx,
        help="Show only listings last seen by the scraper in this year.",
    )

    st.session_state["selected_year_label"] = selected_label
    return None if selected_label == "All years" else int(selected_label)


def render_price_filter(page: str = "default") -> tuple[int, int]:
    """
    Render a synchronised price-range slider + Min/Max number inputs.
    Each page passes a unique `page` identifier so filters are independent.

    Persistence across page navigation works via non-widget storage keys
    (_stored_pmin_<page> / _stored_pmax_<page>).  Streamlit garbage-collects
    widget keys when the widget isn't rendered (i.e. on another page), but it
    never clears plain session_state entries, so we store intent there and
    re-seed the widget keys on first render after navigation.
    """
    ceiling = load_max_price()

    # Plain session_state (non-widget) — survives page navigation
    store_min  = f"_stored_pmin_{page}"
    store_max  = f"_stored_pmax_{page}"

    # Widget keys — may be cleared by Streamlit when page is not active
    min_key    = f"_pmin_{page}"
    max_key    = f"_pmax_{page}"
    slider_key = f"_slider_{page}"

    # Initialise persistent storage once per browser session
    if store_min not in st.session_state:
        st.session_state[store_min] = 0
    if store_max not in st.session_state:
        st.session_state[store_max] = ceiling

    # Re-seed widget keys from storage when returning to this page
    if min_key not in st.session_state:
        st.session_state[min_key] = st.session_state[store_min]
    if max_key not in st.session_state:
        st.session_state[max_key] = st.session_state[store_max]
    if slider_key not in st.session_state:
        st.session_state[slider_key] = (
            st.session_state[store_min],
            st.session_state[store_max],
        )

    def _on_slider():
        lo, hi = st.session_state[slider_key]
        st.session_state[min_key]   = lo
        st.session_state[max_key]   = hi
        st.session_state[store_min] = lo
        st.session_state[store_max] = hi

    def _on_min():
        lo = int(st.session_state[min_key])
        hi = int(st.session_state[max_key])
        lo = min(lo, hi)
        st.session_state[min_key]    = lo
        st.session_state[slider_key] = (lo, hi)
        st.session_state[store_min]  = lo

    def _on_max():
        lo = int(st.session_state[min_key])
        hi = int(st.session_state[max_key])
        hi = max(lo, hi)
        st.session_state[max_key]    = hi
        st.session_state[slider_key] = (lo, hi)
        st.session_state[store_max]  = hi

    st.sidebar.markdown("**Price Range (USD)**")
    st.sidebar.slider(
        "Price Range",
        min_value=0, max_value=ceiling,
        step=5_000, format="$%d",
        key=slider_key, on_change=_on_slider,
        label_visibility="collapsed",
    )
    _c1, _c2 = st.sidebar.columns(2)
    with _c1:
        _c1.number_input(
            "Min ($)", min_value=0, max_value=ceiling,
            step=5_000, key=min_key, on_change=_on_min,
        )
    with _c2:
        _c2.number_input(
            "Max ($)", min_value=0, max_value=ceiling,
            step=5_000, key=max_key, on_change=_on_max,
        )

    return int(st.session_state[store_min]), int(st.session_state[store_max])


def render_broker_filter() -> tuple[str, ...]:
    """
    Render the global Broker multiselect in the sidebar.
    Uses a shared session_state key so the selection persists across all pages.
    Returns a tuple of selected broker names (empty tuple = all brokers).
    """
    all_brokers = load_brokers()
    st.sidebar.multiselect(
        "Broker",
        options=all_brokers,
        default=[],
        placeholder="All brokers",
        key="_broker_filter",
    )
    return tuple(sorted(st.session_state.get("_broker_filter", [])))
