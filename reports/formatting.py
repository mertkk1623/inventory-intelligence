"""Shared value formatting for generated reports.

The UI has its own presentation formatters in ``components.analytics_ui``.
Reports live outside the Streamlit layer, so they keep a small, dependency-free
set of formatters that produce the same textual output.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

DASH = "—"


def quantity(value: int | Decimal | None, unit: str = "") -> str:
    """Format a whole-unit quantity with thousands separators."""

    if value is None:
        return DASH
    number = f"{round(float(value)):,}"
    return f"{number} {unit}".strip()


def decimal(
    value: float | None,
    unit: str = "",
    *,
    places: int = 1,
) -> str:
    """Format a decimal value with thousands separators."""

    if value is None:
        return DASH
    number = f"{float(value):,.{places}f}"
    return f"{number} {unit}".strip()


def days(value: float | None) -> str:
    """Format days of supply, including the zero-consumption case."""

    if value is None:
        return DASH
    return f"{float(value):,.1f} days"


def day(value: date | None) -> str:
    """Format a calendar date for report readers."""

    if value is None:
        return DASH
    return value.strftime("%d %b %Y")


def iso_day(value: date | None) -> str:
    if value is None:
        return DASH
    return value.isoformat()


def timestamp(value: datetime | None) -> str:
    if value is None:
        return DASH
    return value.strftime("%d %b %Y %H:%M")


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"
