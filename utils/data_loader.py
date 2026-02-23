"""
Cached data-loading functions that query the `properties_enriched` view in Supabase.

All heavy queries use @st.cache_data(ttl=3600) so a page re-run does not hit
the database again unless an hour has passed or the user manually clears the cache.

Filters are passed as plain Python primitives (strings, ints, bools) so they
hash correctly as cache keys.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.supabase_client import get_client

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

VIEW = "properties_enriched"

# Columns we always fetch (keeps payload small)
BASE_COLS = (
    "property_id,title,price,base_type,listing_status,"
    "barrio_prefix,barrio_name,pueblo,region_clean,"
    "bedrooms_int,bathrooms_int,broker,is_fsbo,is_optioned,"
    "link,piclink,"
    "first_seen,last_seen,last_seen_year,times_seen,"
    "price_changed,previous_price,price_change_pct,days_tracked"
)


def _to_df(response) -> pd.DataFrame:
    data = response.data or []
    return pd.DataFrame(data)


_PAGE_SIZE = 1_000  # Supabase PostgREST server-side row cap per request


def _fix_piclink(url: str | None) -> str | None:
    """Collapse double-slash after domain (scraping artifact: com//PP/ → com/PP/)."""
    if not url:
        return url
    # Preserve the scheme (https://) but collapse any subsequent //
    scheme, _, rest = url.partition("://")
    return scheme + "://" + rest.replace("//", "/")


def _fetch_all(query_builder) -> pd.DataFrame:
    """
    Paginate through all rows by calling .range() in a loop.
    Supabase caps each response at 1 000 rows regardless of .limit();
    this works around that by requesting successive windows until the
    response comes back shorter than the page size (= last page).
    Also normalises piclink URLs (removes double-slash scraping artifact).
    """
    frames: list[pd.DataFrame] = []
    start = 0
    while True:
        resp = query_builder.range(start, start + _PAGE_SIZE - 1).execute()
        batch = resp.data or []
        if batch:
            frames.append(pd.DataFrame(batch))
        if len(batch) < _PAGE_SIZE:
            break  # last page reached
        start += _PAGE_SIZE
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if "piclink" in df.columns:
        df["piclink"] = df["piclink"].apply(_fix_piclink)
    return df


# ---------------------------------------------------------------------------
# Reference / metadata queries (long TTL — data rarely changes)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=86_400, show_spinner=False)
def load_regions() -> list[str]:
    r = get_client().from_(VIEW).select("region_clean").execute()
    regions = sorted({row["region_clean"] for row in r.data if row["region_clean"]})
    return regions


@st.cache_data(ttl=86_400, show_spinner=False)
def load_base_types() -> list[str]:
    r = get_client().from_(VIEW).select("base_type").execute()
    return sorted({row["base_type"] for row in r.data if row["base_type"]})


@st.cache_data(ttl=86_400, show_spinner=False)
def load_pueblos(regions: tuple[str, ...] | None = None) -> list[str]:
    q = get_client().from_(VIEW).select("pueblo,region_clean")
    if regions:
        q = q.in_("region_clean", list(regions))
    r = q.execute()
    return sorted({row["pueblo"] for row in r.data if row["pueblo"]})


@st.cache_data(ttl=86_400, show_spinner=False)
def load_barrio_prefixes() -> list[str]:
    r = get_client().from_(VIEW).select("barrio_prefix").execute()
    return sorted({row["barrio_prefix"] for row in r.data if row["barrio_prefix"]})


@st.cache_data(ttl=86_400, show_spinner=False)
def load_available_years() -> list[int]:
    """Return sorted list of years present in last_seen_year."""
    r = get_client().from_(VIEW).select("last_seen_year").execute()
    years = sorted(
        {int(row["last_seen_year"]) for row in r.data if row.get("last_seen_year")},
        reverse=True,
    )
    return years


# ---------------------------------------------------------------------------
# Main property query (1-hour TTL)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3_600, show_spinner=False)
def load_properties(
    regions: tuple[str, ...] = (),
    base_types: tuple[str, ...] = (),
    listing_statuses: tuple[str, ...] = (),
    price_min: float = 0,
    price_max: float = 50_000_000,
    min_bedrooms: int = 0,
    min_bathrooms: int = 0,
    pueblos: tuple[str, ...] = (),
    barrio_prefixes: tuple[str, ...] = (),
    hide_optioned: bool = False,
    fsbo_only: bool = False,
    year: int | None = None,
) -> pd.DataFrame:
    """Return a DataFrame matching all active filters."""
    q = get_client().from_(VIEW).select(BASE_COLS)

    if regions:
        q = q.in_("region_clean", list(regions))
    if base_types:
        q = q.in_("base_type", list(base_types))
    if listing_statuses:
        q = q.in_("listing_status", list(listing_statuses))
    if pueblos:
        q = q.in_("pueblo", list(pueblos))
    if barrio_prefixes:
        q = q.in_("barrio_prefix", list(barrio_prefixes))

    q = q.gte("price", price_min).lte("price", price_max)

    if min_bedrooms:
        q = q.gte("bedrooms_int", min_bedrooms)
    if min_bathrooms:
        q = q.gte("bathrooms_int", min_bathrooms)
    if hide_optioned:
        q = q.eq("is_optioned", False)
    if fsbo_only:
        q = q.eq("is_fsbo", True)

    # Global year filter: include only records where last_seen is in this year
    if year is not None:
        q = q.gte("last_seen", f"{year}-01-01").lte("last_seen", f"{year}-12-31")

    # Paginate to bypass the 1 000-row per-request server cap
    return _fetch_all(q)


# ---------------------------------------------------------------------------
# Aggregate / KPI queries (used on the Home page)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3_600, show_spinner=False)
def load_kpi_summary(regions: tuple[str, ...] = (), year: int | None = None) -> dict:
    """Return top-level KPI numbers."""
    df = load_properties(regions=regions, year=year)
    if df.empty:
        return {}
    return {
        "total": len(df),
        "median_price": df["price"].median(),
        "avg_price": df["price"].mean(),
        "pct_optioned": df["is_optioned"].mean() * 100,
        "price_drops": int(df["price_changed"].sum()),
    }


@st.cache_data(ttl=3_600, show_spinner=False)
def load_counts_by_region(regions: tuple[str, ...] = (), year: int | None = None) -> pd.DataFrame:
    df = load_properties(regions=regions, year=year)
    if df.empty:
        return pd.DataFrame()
    return df.groupby("region_clean").size().reset_index(name="count")


@st.cache_data(ttl=3_600, show_spinner=False)
def load_counts_by_type(regions: tuple[str, ...] = (), year: int | None = None) -> pd.DataFrame:
    df = load_properties(regions=regions, year=year)
    if df.empty:
        return pd.DataFrame()
    return df.groupby("base_type").size().reset_index(name="count").sort_values("count", ascending=False)


@st.cache_data(ttl=3_600, show_spinner=False)
def load_status_breakdown(regions: tuple[str, ...] = (), year: int | None = None) -> pd.DataFrame:
    df = load_properties(regions=regions, year=year)
    if df.empty:
        return pd.DataFrame()
    return df.groupby("listing_status").size().reset_index(name="count")


@st.cache_data(ttl=3_600, show_spinner=False)
def load_top_brokers(regions: tuple[str, ...] = (), year: int | None = None, top_n: int = 10) -> pd.DataFrame:
    df = load_properties(regions=regions, year=year)
    if df.empty:
        return pd.DataFrame()
    df = df[~df["is_fsbo"]]  # exclude FSBO for broker ranking
    return (
        df.groupby("broker")
        .size()
        .reset_index(name="listings")
        .sort_values("listings", ascending=False)
        .head(top_n)
    )
