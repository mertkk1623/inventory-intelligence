"""Welcome and Getting Started screen.

The page is the product's front door: hero copy, an eight-step workflow, the
verified Excel contract, the synthetic demo disclosure, a fact-checked privacy
statement, the roadmap and the current version/status.

Every string is resolved through :mod:`utils.i18n`, so the page is complete in
both English and Turkish. The privacy statement describes the behaviour that
actually exists in the code: local read/validate, optional AI, and engine
values plus length-capped text fields sent to the provider only when a key is
configured and an AI button is pressed.
"""

from __future__ import annotations

import hashlib
from html import escape

import streamlit as st

from ai.settings import load_settings
from components.quick_start import render_quick_start
from components.ui import icon, section_header
from components.validation_report import render_validation_result
from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB
from core.schema import SHEET_SPECS
from utils.data_loader import load_demo_dataset, load_uploaded_dataset
from utils.i18n import t
from utils.session_state import (
    PAGE_OVERVIEW,
    UPLOAD_RESULT_KEY,
    UPLOAD_SIGNATURE_KEY,
    reset_upload_state,
    set_page,
    uploader_key,
)

_DEMO_ERROR_KEY = "ii_demo_error"

APP_VERSION_LABEL = "Inventory Intelligence V1"
APP_STATUS_LABEL = "Development Complete — Pre-Release"

# The eight-step workflow required by the product brief. Keys are English
# source strings so they also serve as translation keys.
_STEPS: tuple[tuple[str, str, str, str], ...] = (
    (
        "01",
        "Download Excel Template",
        "Start with the workbook that already contains the required sheets and "
        "columns.",
        "download",
    ),
    (
        "02",
        "Enter Product and Stock Data",
        "Add your SKU, opening stock, safety stock and planning parameters.",
        "box",
    ),
    (
        "03",
        "Upload Excel File",
        "Drop in the completed workbook. Every sheet is validated before loading.",
        "upload",
    ),
    (
        "04",
        "Review Inventory Dashboard",
        "Check current stock, days of supply, the reorder point and the suggested "
        "order quantity.",
        "table",
    ),
    (
        "05",
        "Analyze Consumption",
        "Inspect daily and weekly OUT consumption, including zero-consumption "
        "days.",
        "query_stats",
    ),
    (
        "06",
        "Review Replenishment Recommendations",
        "Compare inventory position with the reorder point and review open "
        "purchase orders.",
        "inventory_2",
    ),
    (
        "07",
        "Ask AI Analyst",
        "Optionally ask the AI analyst to explain the numbers in plain language.",
        "sparkle",
    ),
    (
        "08",
        "Export Excel or PDF Reports",
        "Download a formatted Excel workbook or a presentation-ready PDF for the "
        "selected report date.",
        "sheet",
    ),
)

_SHEET_PURPOSE: dict[str, str] = {
    "Product Master": (
        "One row describing your single SKU, its opening stock and the planning "
        "parameters used by later modules."
    ),
    "Stock Movements": (
        "Dated IN and OUT transactions recorded on or after the opening stock "
        "date."
    ),
    "Open Orders": (
        "Purchase orders that have not been delivered yet. They are treated as "
        "incoming supply and never added to Current Stock."
    ),
}

_RULES: tuple[str, ...] = (
    "Exactly one product row with a unique Product Code.",
    "Movement and order quantities must be positive whole numbers.",
    "Opening Stock and Safety Stock must be zero or greater.",
    "Transaction Type must be IN or OUT.",
    "Dates must be valid Excel dates.",
    "No movement may be dated before the Opening Stock Date.",
    "Order numbers must be unique.",
    "Required sheet and column names must stay unchanged.",
)

_COMPLETED: tuple[str, ...] = (
    "Package 1 — Foundation",
    "Package 2 — Inventory Calculation Engine",
    "Package 3 — Analytics and Dashboard",
    "Package 4 — Excel and PDF Reporting",
    "Package 5 — AI Intelligence Layer",
)

_PLANNED: tuple[str, ...] = (
    "V2 — ABC Analysis and Demand Forecasting",
    "V3 — Stock Optimization",
    "V4 — Multi-SKU and Multi-Warehouse Support",
    "V5 — ERP Integration and Advanced Automation",
)


def render_welcome() -> None:
    """Render the full welcome experience."""

    st.markdown(_hero_html(), unsafe_allow_html=True)

    # Quick Start is the first actionable block: it lets a visitor run the app
    # and the AI layer in one click, and it sits directly above the upload area.
    render_quick_start()

    st.markdown(
        section_header(
            t("Get Started"),
            t("Choose how you want to begin"),
            t(
                "Upload your own workbook, or load the bundled demo workbook to "
                "compare it with the sample scenarios above."
            ),
        ),
        unsafe_allow_html=True,
    )
    _render_upload_cards()

    demo_error = st.session_state.get(_DEMO_ERROR_KEY)
    if demo_error is not None:
        render_validation_result(demo_error)

    st.markdown(
        section_header(
            t("How It Works"),
            t("Eight steps from workbook to decision"),
            t(
                "Inventory Intelligence validates your Excel file before any "
                "analysis starts, so every later decision is based on clean data."
            ),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(_steps_html(), unsafe_allow_html=True)

    st.markdown(
        section_header(
            t("Excel Data Requirements"),
            t("A simple three-sheet workbook"),
            t(
                "Keep the template structure intact. The validator checks sheet "
                "names, column names, data types and cross-sheet rules."
            ),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(_sheet_cards_html(), unsafe_allow_html=True)

    st.markdown(
        section_header(t("Data rules"), t("What the validator enforces")),
        unsafe_allow_html=True,
    )
    st.markdown(_rules_html(), unsafe_allow_html=True)

    st.markdown(
        section_header(
            t("Demo Data"),
            t("A synthetic dataset you can explore safely"),
            t(
                "The bundled demo workbook is generated for demonstration only. "
                "It is not real company data and it is never mixed with your own "
                "uploads: loading the demo replaces any active upload, and "
                "uploading a file replaces the demo."
            ),
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        section_header(
            t("Data Privacy"),
            t("What happens to your workbook"),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(_privacy_html(), unsafe_allow_html=True)

    st.markdown(
        section_header(
            t("Roadmap"),
            t("Where the product stands today"),
            t("Current version: V1"),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(_roadmap_html(), unsafe_allow_html=True)

    st.markdown(
        section_header(t("Project Status"), t("Version and release state")),
        unsafe_allow_html=True,
    )
    st.markdown(_status_html(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------


def _render_upload_cards() -> None:
    """Render the bundled demo loader and the real upload area.

    Template and sample downloads live in the Quick Start panel above, so this
    section stays focused on the two remaining entry points: the bundled demo
    workbook and the user's own file.
    """

    demo_column, upload_column = st.columns(2, gap="large")

    with demo_column:
        with st.container(border=True):
            st.markdown(
                f'<div class="ii-action-icon green">{icon("play", 20)}</div>'
                f'<div class="ii-action-title">{escape(t("Try Demo Data"))}</div>'
                '<p class="ii-action-text">'
                f"{escape(t('Explore the workspace with a synthetic single-SKU dataset. Demo data is generated for demonstration only and is not real company data.'))}"
                "</p>",
                unsafe_allow_html=True,
            )
            if st.button(
                t("Load Demo Data"),
                type="secondary",
                width="stretch",
                icon=":material/play_arrow:",
                key="load_demo",
            ):
                result = load_demo_dataset()
                if result.is_valid:
                    st.session_state.pop(_DEMO_ERROR_KEY, None)
                    reset_upload_state()
                    set_page(PAGE_OVERVIEW)
                    st.rerun()
                else:
                    st.session_state[_DEMO_ERROR_KEY] = result

    with upload_column:
        with st.container(border=True):
            st.markdown(
                f'<div class="ii-action-icon amber">{icon("upload", 20)}</div>'
                f'<div class="ii-action-title">{escape(t("Upload Your Excel"))}</div>'
                '<p class="ii-action-text">'
                f"{escape(t('Already have a completed workbook? Upload it and we will validate every sheet before it becomes active. XLSX only, up to {size} MB.', size=MAX_UPLOAD_SIZE_MB))}"
                "</p>",
                unsafe_allow_html=True,
            )
            uploaded_file = st.file_uploader(
                t("Upload your Excel workbook"),
                type=list(ALLOWED_EXTENSIONS),
                key=uploader_key(),
                label_visibility="collapsed",
                max_upload_size=MAX_UPLOAD_SIZE_MB,
                help=t(
                    "Use the Inventory Intelligence template. Only .xlsx files "
                    "up to {size} MB are supported.",
                    size=MAX_UPLOAD_SIZE_MB,
                ),
            )

    if uploaded_file is not None:
        _handle_upload(uploaded_file)


def _handle_upload(uploaded_file) -> None:
    payload = uploaded_file.getvalue()
    signature = hashlib.sha256(payload).hexdigest()

    if st.session_state.get(UPLOAD_SIGNATURE_KEY) != signature:
        result = load_uploaded_dataset(uploaded_file)
        st.session_state[UPLOAD_SIGNATURE_KEY] = signature
        st.session_state[UPLOAD_RESULT_KEY] = result
        # A new upload replaces the previous attempt, so a stale demo error
        # must not be shown next to the upload result.
        st.session_state.pop(_DEMO_ERROR_KEY, None)

        if result.is_valid:
            st.session_state.pop(_DEMO_ERROR_KEY, None)
            set_page(PAGE_OVERVIEW)
            st.rerun()

    result = st.session_state.get(UPLOAD_RESULT_KEY)
    if result is not None and not result.is_valid:
        render_validation_result(result)


def _hero_html() -> str:
    chips = (
        ("Single-SKU workspace", "box"),
        ("Local validation", "shield"),
        ("Excel-native", "sheet"),
    )
    chip_html = "".join(
        f'<span class="ii-chip">{icon(icon_name, 13)}{escape(t(label))}</span>'
        for label, icon_name in chips
    )
    sheets = "".join(
        f'<div class="ii-file-row">'
        f'<div class="ii-file-icon">{icon("sheet", 14)}</div>'
        f"<div><div class=\"ii-file-name\">{escape(t(spec.name))}</div>"
        f'<div class="ii-file-meta">{escape(t(_SHEET_PURPOSE[spec.name]))}</div></div>'
        f'<div class="ii-file-check">{icon("check", 15)}</div>'
        "</div>"
        for spec in SHEET_SPECS
    )
    return (
        '<div class="ii-hero">'
        '<div class="ii-hero-copy">'
        # The product name is a brand and is never translated, so the eyebrow
        # keeps Latin casing rules while the rest of the page may be Turkish.
        '<div class="ii-eyebrow" lang="en"><span class="dot"></span>'
        f"{escape(t('Inventory Intelligence · V1'))}</div>"
        f"<h1>{escape(t('Inventory Intelligence'))}</h1>"
        f'<p class="ii-hero-sub">{escape(t("AI-powered inventory analytics and replenishment decision support."))}</p>'
        f"<p>{escape(t('The application helps users understand stock levels, consumption patterns, replenishment requirements and inventory risks using structured Excel data.'))}</p>"
        f'<div class="ii-hero-chips">{chip_html}</div>'
        "</div>"
        '<div class="ii-hero-panel">'
        f'<div class="ii-panel-title">{escape(t("Your workbook"))}</div>'
        f"{sheets}"
        "</div>"
        "</div>"
    )


def _steps_html() -> str:
    steps = "".join(
        f'<div class="ii-step">'
        f'<div class="ii-step-top"><span class="ii-step-num">{number}</span>'
        f'<span class="ii-step-icon">{icon(icon_name, 16)}</span></div>'
        f"<h4>{escape(t(title))}</h4>"
        f"<p>{escape(t(description))}</p>"
        "</div>"
        for number, title, description, icon_name in _STEPS
    )
    return f'<div class="ii-steps">{steps}</div>'


def _sheet_cards_html() -> str:
    cards = "".join(
        f'<div class="ii-sheet-card">'
        f'<div class="ii-sheet-head"><span class="ii-sheet-icon">'
        f'{icon("table", 16)}</span><span class="ii-sheet-name">'
        f"{escape(t(spec.name))}</span></div>"
        f'<p class="ii-sheet-desc">{escape(t(_SHEET_PURPOSE[spec.name]))}</p>'
        '<div class="ii-col-tags">'
        + "".join(
            f'<span class="ii-col-tag">{escape(column)}</span>'
            for column in spec.required_columns
        )
        + "</div></div>"
        for spec in SHEET_SPECS
    )
    return f'<div class="ii-sheet-grid">{cards}</div>'


def _rules_html() -> str:
    rules = "".join(
        f'<div class="ii-rule">{icon("check", 15)}<span>{escape(t(rule))}</span></div>'
        for rule in _RULES
    )
    return f'<div class="ii-rules">{rules}</div>'


def _privacy_html() -> str:
    """Return the privacy banner, matching the behaviour in the code."""

    configured = load_settings().is_configured
    if configured:
        message = (
            "Your workbook is read and validated inside this session. The file "
            "is never written to disk, never uploaded to a database and is "
            "discarded when the session ends. The AI layer is optional: it stays "
            "switched off unless an API key is configured, and it only runs when "
            "you press an AI button. When it runs, the request contains the "
            "calculated engine values plus short, length-limited text fields "
            "(product name, movement descriptions) sent to the configured "
            "provider. An API key is configured in this deployment, so an AI "
            "request is sent only when you click an AI button."
        )
    else:
        message = (
            "Your workbook is read and validated inside this session. The file "
            "is never written to disk, never uploaded to a database and is "
            "discarded when the session ends. The AI layer is optional: it stays "
            "switched off unless an API key is configured, and it only runs when "
            "you press an AI button. When it runs, the request contains the "
            "calculated engine values plus short, length-limited text fields "
            "(product name, movement descriptions) sent to the configured "
            "provider. No API key is configured in this deployment, so no data "
            "leaves this session."
        )
    return (
        f'<div class="ii-privacy">{icon("shield", 15)}'
        f"<span>{escape(t(message))}</span></div>"
    )


def _roadmap_html() -> str:
    completed = "".join(
        f'<div class="ii-road-item done">'
        f'<span class="ii-road-mark">{icon("check", 13)}</span>'
        f"<span>{escape(t(item))}</span>"
        f'<span class="ii-road-tag done">{escape(t("Completed"))}</span>'
        "</div>"
        for item in _COMPLETED
    )
    planned = "".join(
        f'<div class="ii-road-item planned">'
        f'<span class="ii-road-mark">{icon("clock", 13)}</span>'
        f"<span>{escape(t(item))}</span>"
        f'<span class="ii-road-tag planned">{escape(t("Planned"))}</span>'
        "</div>"
        for item in _PLANNED
    )
    return (
        '<div class="ii-road">'
        f'<div class="ii-road-col"><div class="ii-road-head">'
        f'<span class="ii-road-version">V1</span>'
        f'{escape(t("Completed"))}</div>{completed}</div>'
        f'<div class="ii-road-col"><div class="ii-road-head">'
        f'<span class="ii-road-version">{escape(t("FUTURE"))}</span>'
        f'{escape(t("Planned"))}</div>{planned}</div>'
        "</div>"
        f'<div class="ii-road-note">'
        f"{escape(t('The current V1 scope is complete. Future roadmap items are planned enhancements and are not currently available.'))}"
        "</div>"
    )


def _status_html() -> str:
    facts = (
        (t("Version"), t(APP_VERSION_LABEL)),
        (t("Project Status"), t(APP_STATUS_LABEL)),
        (t("Completed packages"), "5 / 5"),
        (t("Automated tests"), "233"),
        (t("Screens"), "7"),
        (t("Interface languages"), "English · Türkçe"),
    )
    cells = "".join(
        f'<div class="ii-detail"><div class="ii-detail-label">{escape(label)}</div>'
        f'<div class="ii-detail-value">{escape(value)}</div></div>'
        for label, value in facts
    )
    return (
        '<div class="ii-status-card">'
        f'<div class="ii-status-head">'
        f'<span class="ii-status-pill">{escape(t("Development Complete — Pre-Release"))}</span>'
        f"<span>{escape(t(APP_VERSION_LABEL))}</span></div>"
        f'<div class="ii-detail-grid">{cells}</div>'
        f'<div class="ii-status-note">'
        f"{escape(t('Local demo build. Not deployed to a public environment and not published as a live product.'))}"
        "</div>"
        "</div>"
    )


__all__ = ["APP_STATUS_LABEL", "APP_VERSION_LABEL", "render_welcome"]
