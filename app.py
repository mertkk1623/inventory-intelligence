"""Inventory Intelligence — Streamlit application entry point."""

from __future__ import annotations

import logging

import streamlit as st

from components.ai_analyst import render_ai_analyst
from components.consumption_analysis import render_consumption_analysis
from components.overview import render_dashboard
from components.replenishment import render_replenishment
from components.reports import render_reports
from components.sidebar import render_sidebar
from components.stock_analysis import render_stock_analysis
from components.styles import inject_global_styles, sync_document_language
from components.welcome import render_welcome
from config import APP_NAME, APP_TAGLINE, PAGE_ICON
from utils.calculation import get_calculation
from utils.i18n import t
from utils.session_state import (
    PAGE_AI_ANALYST,
    PAGE_CONSUMPTION_ANALYSIS,
    PAGE_DASHBOARD,
    PAGE_REPLENISHMENT,
    PAGE_REPORTS,
    PAGE_STOCK_ANALYSIS,
    PAGE_WELCOME,
    get_dataset,
    get_report_date,
)

logger = logging.getLogger(__name__)

# The sidebar is rendered first, so the page title and tab label follow the
# language chosen for the session. The initial title is English, which is also
# the default language.
st.set_page_config(
    page_title=f"{APP_NAME} · {APP_TAGLINE}",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_styles()


def _run_app() -> None:
    page = render_sidebar()
    # The sidebar resolves the language for this run, so the document language
    # is synced afterwards: it drives locale-aware CSS upper-casing.
    sync_document_language()
    dataset = get_dataset()

    if dataset is None or page == PAGE_WELCOME:
        render_welcome()
        return

    report_date = get_report_date(dataset)
    try:
        calculation = get_calculation(dataset, report_date)
    except Exception as exc:
        logger.exception("Inventory calculation failed")
        st.error(
            t(
                "The active dataset could not be calculated. Adjust the report "
                "date or reload the workbook. Details: {error}",
                error=exc,
            )
        )
        return

    if page == PAGE_DASHBOARD:
        render_dashboard(dataset, calculation)
    elif page == PAGE_STOCK_ANALYSIS:
        render_stock_analysis(dataset, calculation)
    elif page == PAGE_CONSUMPTION_ANALYSIS:
        render_consumption_analysis(dataset, calculation)
    elif page == PAGE_REPLENISHMENT:
        render_replenishment(dataset, calculation)
    elif page == PAGE_REPORTS:
        render_reports(dataset, calculation)
    elif page == PAGE_AI_ANALYST:
        render_ai_analyst(dataset, calculation)
    else:
        render_welcome()


try:
    _run_app()
except Exception:
    logger.exception("Unhandled error while rendering Inventory Intelligence")
    st.error(
        t(
            "Something went wrong while rendering this screen. Reload the page "
            "or clear the workspace from the sidebar and try again."
        )
    )
