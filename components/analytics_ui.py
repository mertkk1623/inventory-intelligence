"""Shared presentation helpers for the analytics screens.

All user-facing text and every display format flows through
:mod:`utils.i18n`, which keeps English and Turkish consistent across the seven
screens without touching a single calculation value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape

import streamlit as st

from core.models import InventoryDataset
from utils.i18n import format_date as _format_date
from utils.i18n import format_days as _format_days
from utils.i18n import format_decimal as _format_decimal
from utils.i18n import format_quantity as _format_quantity
from utils.i18n import t


@dataclass(frozen=True)
class KpiItem:
    label: str
    value: str
    meta: str = ""
    tone: str = ""


def format_quantity(value: int | float | Decimal | None, unit: str = "") -> str:
    """Format a whole-unit quantity using the active language's separators."""

    return _format_quantity(value, unit)


def format_decimal(
    value: Decimal | float | int | None,
    unit: str = "",
    *,
    places: int = 1,
) -> str:
    """Format a decimal value for KPI and table display."""

    return _format_decimal(value, unit, places=places)


def format_days(value: Decimal | float | int | None) -> str:
    """Format days of supply, including the zero-consumption case."""

    return _format_days(value)


def format_date(value: date | None) -> str:
    """Format a calendar date for the active language."""

    return _format_date(value)


def page_header(
    title: str,
    subtitle: str,
    dataset: InventoryDataset,
    *,
    as_of: date | None = None,
) -> str:
    """Render the shared analytics page heading with a dataset badge."""

    badge_class = "demo" if dataset.is_demo else "upload"
    badge_label = t("Demo data" if dataset.is_demo else "Uploaded file")
    as_of_html = (
        f'<div class="ii-page-asof">'
        f"{escape(t('As of {date}', date=format_date(as_of)))}</div>"
        if as_of is not None
        else ""
    )
    return (
        '<div class="ii-page-head">'
        "<div>"
        '<div class="ii-page-eyebrow">'
        f"{escape(t('Data Overview'))} · {escape(dataset.filename)}</div>"
        f'<h1 class="ii-page-title">{escape(title)}</h1>'
        f'<p class="ii-page-sub">{escape(subtitle)}</p>'
        f"{as_of_html}"
        "</div>"
        f'<span class="ii-badge {badge_class}">{escape(badge_label)}</span>'
        "</div>"
    )


def kpi_cards(
    items: list[KpiItem] | tuple[KpiItem, ...],
    *,
    columns: int = 4,
) -> str:
    """Render a responsive row of design-system KPI cards."""

    cards = "".join(
        f'<div class="ii-metric{" tone-" + escape(item.tone) if item.tone else ""}">'
        f'<div class="ii-metric-label">{escape(item.label)}</div>'
        f'<div class="ii-metric-value">{escape(item.value)}</div>'
        f'<div class="ii-metric-meta">{escape(item.meta)}</div>'
        "</div>"
        for item in items
    )
    modifier = " cols-2" if columns == 2 else ""
    return f'<div class="ii-metrics{modifier}">{cards}</div>'


def card_header(title: str, subtitle: str = "") -> str:
    """Render a compact heading for a bordered chart or table card."""

    subtitle_html = (
        f'<div class="ii-card-sub">{escape(subtitle)}</div>' if subtitle else ""
    )
    return (
        '<div class="ii-card-head">'
        f'<div class="ii-card-title">{escape(title)}</div>'
        f"{subtitle_html}"
        "</div>"
    )


def chart(figure, *, key: str) -> None:
    """Render a Plotly figure with the shared, restrained chart chrome."""

    st.plotly_chart(
        figure,
        width="stretch",
        config={
            "displayModeBar": False,
            "displaylogo": False,
            "responsive": True,
        },
        key=key,
    )


def empty_state(title: str, message: str) -> None:
    """Render a neutral empty state inside a card."""

    st.markdown(
        f'<div class="ii-empty"><div class="ii-empty-title">{escape(title)}</div>'
        f'<div class="ii-empty-text">{escape(message)}</div></div>',
        unsafe_allow_html=True,
    )


__all__ = [
    "KpiItem",
    "card_header",
    "chart",
    "empty_state",
    "format_date",
    "format_days",
    "format_decimal",
    "format_quantity",
    "kpi_cards",
    "page_header",
]
