"""
Shared sidebar components rendered on every page.
Stores selections in st.session_state so values persist across page navigation.
"""
from __future__ import annotations

import streamlit as st

from utils.data_loader import load_available_years

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
