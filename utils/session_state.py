"""Streamlit session-state helpers.

Only one dataset is active at a time. Activating demo data replaces any
uploaded dataset and vice versa, which guarantees that demo and user data
can never be mixed in the same workspace.

The report date is shared by every analytics screen. It is stored separately
from the date-input widget so it can be clamped when a new dataset is
activated.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from core.models import InventoryDataset

DATASET_KEY = "ii_dataset"
PAGE_KEY = "ii_page"
PENDING_PAGE_KEY = "ii_pending_page"
NAV_WIDGET_KEY = "ii_nav_widget"
UPLOAD_SIGNATURE_KEY = "ii_upload_signature"
UPLOAD_RESULT_KEY = "ii_upload_result"
UPLOADER_NONCE_KEY = "ii_uploader_nonce"
REPORT_DATE_KEY = "ii_report_date"
REPORT_DATE_INPUT_KEY = "ii_report_date_input"
REPORT_DATE_SIGNATURE_KEY = "ii_report_date_signature"
CALCULATION_KEY = "ii_calculation"
CALCULATION_SIGNATURE_KEY = "ii_calculation_signature"

PAGE_WELCOME = "Getting Started"
PAGE_DASHBOARD = "Dashboard"
PAGE_STOCK_ANALYSIS = "Stock Analysis"
PAGE_CONSUMPTION_ANALYSIS = "Consumption Analysis"
PAGE_REPLENISHMENT = "Replenishment Planning"
PAGE_REPORTS = "Reports"
PAGE_AI_ANALYST = "AI Analyst"

# Pages that require an active dataset, in sidebar order.
ANALYTICS_PAGES: tuple[str, ...] = (
    PAGE_DASHBOARD,
    PAGE_STOCK_ANALYSIS,
    PAGE_CONSUMPTION_ANALYSIS,
    PAGE_REPLENISHMENT,
    PAGE_REPORTS,
    PAGE_AI_ANALYST,
)

# Backwards-compatible alias for the page name used before Package 3.
PAGE_OVERVIEW = PAGE_DASHBOARD


def get_dataset() -> InventoryDataset | None:
    dataset = st.session_state.get(DATASET_KEY)
    return dataset if isinstance(dataset, InventoryDataset) else None


def set_dataset(dataset: InventoryDataset) -> None:
    """Activate a dataset and reset date/calculation state for it."""

    st.session_state[DATASET_KEY] = dataset
    reset_report_date()
    reset_calculation()
    _reset_ai_state()


def clear_dataset() -> None:
    st.session_state.pop(DATASET_KEY, None)
    reset_report_date()
    reset_calculation()
    _reset_ai_state()


def _reset_ai_state() -> None:
    """Drop cached AI answers so a new dataset never reuses an old one."""

    from ai.session import clear_ai_state

    clear_ai_state()


def is_demo_mode() -> bool:
    dataset = get_dataset()
    return bool(dataset and dataset.is_demo)


def set_page(page: str) -> None:
    """Navigate programmatically.

    The page is stored separately from the radio widget key so it can be
    changed after the sidebar has already rendered. The pending value is
    applied to the widget at the start of the next script run.
    """

    st.session_state[PAGE_KEY] = page
    st.session_state[PENDING_PAGE_KEY] = page


def set_current_page(page: str) -> None:
    """Record the page selected by the navigation widget."""

    st.session_state[PAGE_KEY] = page


def get_page() -> str:
    return st.session_state.get(PAGE_KEY, PAGE_WELCOME)


def report_date_bounds(
    dataset: InventoryDataset,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    """Return the inclusive report-date range for a dataset.

    The lower bound is the Opening Stock Date and the upper bound is today.
    A workbook whose opening date is in the future would otherwise produce an
    inverted range, so the opening date becomes the effective upper bound in
    that edge case.
    """

    opening = dataset.product.opening_stock_date
    current_day = today or date.today()
    return opening, max(opening, current_day)


def get_report_date(
    dataset: InventoryDataset,
    *,
    today: date | None = None,
) -> date:
    """Return the shared report date, clamped to the dataset bounds."""

    lower, upper = report_date_bounds(dataset, today=today)
    value = st.session_state.get(REPORT_DATE_KEY)
    if not isinstance(value, date):
        value = upper
    value = min(max(value, lower), upper)
    st.session_state[REPORT_DATE_KEY] = value
    return value


def set_report_date(value: date) -> None:
    st.session_state[REPORT_DATE_KEY] = value


def reset_report_date() -> None:
    st.session_state.pop(REPORT_DATE_KEY, None)
    st.session_state.pop(REPORT_DATE_INPUT_KEY, None)
    st.session_state.pop(REPORT_DATE_SIGNATURE_KEY, None)


def report_date_signature(dataset: InventoryDataset) -> tuple:
    """Identify the dataset that owns the current date-input widget state."""

    return (
        dataset.source,
        dataset.filename,
        dataset.product.opening_stock_date,
        dataset.movement_count,
        dataset.open_order_count,
    )


def reset_calculation() -> None:
    st.session_state.pop(CALCULATION_KEY, None)
    st.session_state.pop(CALCULATION_SIGNATURE_KEY, None)


def uploader_key() -> str:
    nonce = st.session_state.get(UPLOADER_NONCE_KEY, 0)
    return f"ii_upload_{nonce}"


def reset_upload_state(*, clear_widget: bool = True) -> None:
    """Forget the last uploaded file and validation result.

    Incrementing the uploader nonce gives Streamlit a brand-new widget, which
    clears the previous file selection. Call this before the uploader is
    instantiated in the current script run.
    """

    st.session_state.pop(UPLOAD_SIGNATURE_KEY, None)
    st.session_state.pop(UPLOAD_RESULT_KEY, None)
    if clear_widget:
        st.session_state[UPLOADER_NONCE_KEY] = (
            st.session_state.get(UPLOADER_NONCE_KEY, 0) + 1
        )


def clear_workspace() -> None:
    """Remove the active dataset and all upload-related state."""

    clear_dataset()
    reset_upload_state()
    set_page(PAGE_WELCOME)
