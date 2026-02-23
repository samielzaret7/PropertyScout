"""
Formatting helpers shared across dashboard pages.
"""
from __future__ import annotations


def fmt_price(value: float | None) -> str:
    """Format a price as '$1,250,000'."""
    if value is None:
        return "N/A"
    return f"${value:,.0f}"


def fmt_pct(value: float | None, decimals: int = 1) -> str:
    """Format a percentage value as '12.3 %'."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


# Human-readable labels for internal enum values
LISTING_STATUS_LABELS = {
    "standard": "Standard",
    "new_construction": "New Construction",
    "repo": "Repo / REO",
}

REGION_LABELS = {
    "metro": "Metro",
    "north": "North",
    "south": "South",
    "east": "East",
    "west": "West",
}

REGION_COLORS = {
    "metro": "#1565C0",
    "north": "#2E7D32",
    "south": "#E65100",
    "east": "#6A1B9A",
    "west": "#00838F",
}

BEDROOMS_OPTIONS = [
    (0, "Any"),
    (1, "1+"),
    (2, "2+"),
    (3, "3+"),
    (4, "4+"),
    (5, "5+"),
    (6, "6+"),
]

BATHROOMS_OPTIONS = [
    (0, "Any"),
    (1, "1+"),
    (2, "2+"),
    (3, "3+"),
    (4, "4+"),
    (5, "5+"),
]


def beds_label(val: int | None) -> str:
    if val is None or val == 0:
        return "—"
    return f"{val}+" if val >= 6 else str(val)


def baths_label(val: int | None) -> str:
    return beds_label(val)
