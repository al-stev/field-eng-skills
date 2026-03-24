"""Shared data transformation utilities for deep analytics."""

from datetime import date
from typing import Any

import pandas as pd


def safe_value(val: Any, default: Any = None) -> Any:
    """Convert pandas NA/NaN/NaT to None for JSON serialization."""
    if pd.isna(val):
        return default
    return val


def format_date(d: Any) -> str | None:
    """Format a date value to ISO string, or None if invalid."""
    if pd.isna(d):
        return None
    if isinstance(d, str):
        return d
    if hasattr(d, 'isoformat'):
        return d.isoformat()
    return str(d)


def kebab_case(name: str) -> str:
    """Convert customer name to kebab-case for output paths."""
    import re
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def period_dict(start: date | str, end: date | str) -> dict:
    """Create a standard period dict for PAGE_DATA."""
    return {
        "start": format_date(start),
        "end": format_date(end),
    }
