"""Quick Start and Demo Data panel for the Getting Started screen.

The panel sits directly above the upload area and gives a first-time visitor
three ways to move in one click:

* **Run the AI demo** generates a fully populated scenario workbook, validates
  it through the real engine and activates it, so the whole application is
  explorable without preparing any data.
* **Download the blank template** hands over a format-guided workbook whose
  headers are generated from :mod:`core.schema`.
* **Download a populated sample** gives the same dataset as a file, so it can
  be inspected, edited and re-uploaded through the normal upload path.

Every scenario is a *single* product. V1 supports one product row per
workbook, so the panel contrasts turnover patterns (stockout risk, dead stock,
negative balance, fast mover) instead of claiming a multi-SKU ABC analysis.
"""

from __future__ import annotations

import logging
from html import escape

import streamlit as st

from components.ui import icon, section_header
from utils.data_loader import load_sample_dataset
from utils.i18n import t
from utils.sample_data import (
    BLANK_TEMPLATE_FILENAME,
    DEFAULT_SCENARIO_KEY,
    SAMPLE_SCENARIOS,
    cached_blank_template_bytes,
    cached_sample_workbook_bytes,
    sample_filename,
)
from utils.session_state import (
    PAGE_OVERVIEW,
    reset_upload_state,
    set_page,
)

logger = logging.getLogger(__name__)

SAMPLE_ERROR_KEY = "ii_sample_error"
SAMPLE_SELECT_KEY = "ii_sample_scenario"
SAMPLE_DOWNLOAD_KEY = "ii_sample_download_scenario"

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# The three bullet points under the buttons. Keys are English source strings so
# they double as translation keys.
_DEMO_NOTES: tuple[str, ...] = (
    "The sample set ships one product per workbook, because V1 plans a single "
    "SKU at a time. The four scenarios contrast turnover patterns: stockout "
    "risk, dead stock, a negative balance and a fast mover.",
    "Every AI feature is exercised: the inventory overview, findings, risks "
    "and recommended actions, the consumption pattern analysis, the "
    "replenishment explanation and the natural-language analyst.",
    "The deliberate outliers are real, not decoration: an overdue purchase "
    "order, a bulk shipment picked before its receipt, a seasonal demand "
    "surge and roughly 4,500 units of idle capital.",
)


def render_quick_start() -> None:
    """Render the Quick Start panel above the upload area."""

    st.markdown(
        section_header(
            t("Quick Start & Demo Data"),
            t("Try the app and the AI without preparing a file"),
            t(
                "Load a realistic dataset straight into the workspace, or "
                "download a workbook to inspect and adapt. Nothing here "
                "touches your own files."
            ),
        ),
        unsafe_allow_html=True,
    )

    _render_scenario_notes()
    _render_buttons()

    error = st.session_state.get(SAMPLE_ERROR_KEY)
    if error is not None:
        from components.validation_report import render_validation_result

        render_validation_result(error)
        if st.button(
            t("Dismiss"),
            key="dismiss_sample_error",
            icon=":material/close:",
        ):
            st.session_state.pop(SAMPLE_ERROR_KEY, None)
            st.rerun()


# ---------------------------------------------------------------------------
# Scenario primer
# ---------------------------------------------------------------------------


def _render_scenario_notes() -> None:
    """Show what each scenario is designed to demonstrate."""

    cards = "".join(
        f'<div class="ii-scenario-card">'
        f'<div class="ii-scenario-head">'
        f'<span class="ii-scenario-name">{escape(t(scenario.name))}</span>'
        f'<span class="ii-scenario-code">{escape(scenario.product_code)}</span>'
        "</div>"
        f'<p class="ii-scenario-text">{escape(t(scenario.summary))}</p>'
        "</div>"
        for scenario in SAMPLE_SCENARIOS
    )
    st.markdown(
        f'<div class="ii-scenario-grid">{cards}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _render_buttons() -> None:
    demo_column, template_column, sample_column = st.columns(3, gap="large")

    with demo_column:
        _render_demo_action()

    with template_column:
        _render_template_action()

    with sample_column:
        _render_download_action()

    notes = "".join(
        f'<div class="ii-demo-note">{icon("check", 14)}<span>{escape(t(note))}</span></div>'
        for note in _DEMO_NOTES
    )
    st.markdown(f'<div class="ii-demo-notes">{notes}</div>', unsafe_allow_html=True)


def _render_demo_action() -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="ii-action-icon green">{icon("sparkle", 20)}</div>'
            f'<div class="ii-action-title">'
            f'{escape(t("Run the AI demo"))}</div>'
            '<p class="ii-action-text">'
            f"{escape(t('Load a populated scenario and open the dashboard immediately. No download, no upload.'))}"
            "</p>",
            unsafe_allow_html=True,
        )

        scenario = _scenario_picker(SAMPLE_SELECT_KEY, label=t("Demo scenario"))

        if st.button(
            t("🚀 Run the AI demo now"),
            type="primary",
            width="stretch",
            icon=":material/rocket_launch:",
            key="load_sample_demo",
            help=t(
                "Generates the selected scenario, validates it and opens the "
                "Overview Dashboard."
            ),
        ):
            _activate_scenario(scenario.key)


def _render_template_action() -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="ii-action-icon blue">{icon("download", 20)}</div>'
            f'<div class="ii-action-title">'
            f'{escape(t("Blank data template"))}</div>'
            '<p class="ii-action-text">'
            f"{escape(t('Start from a workbook with the exact required sheets and column headers, plus a Read Me guide.'))}"
            "</p>",
            unsafe_allow_html=True,
        )

        try:
            payload = cached_blank_template_bytes()
        except Exception:  # pragma: no cover - defensive guard
            logger.exception("Could not generate the blank template")
            st.error(t("The blank template could not be generated."))
            return

        st.download_button(
            t("📥 Download blank template"),
            data=payload,
            file_name=BLANK_TEMPLATE_FILENAME,
            mime=_XLSX_MIME,
            type="secondary",
            width="stretch",
            icon=":material/download:",
            key="download_blank_template",
            help=t(
                "Empty sheets with the exact headers, a Read Me guide and a "
                "dropdown for Transaction Type."
            ),
        )


def _render_download_action() -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="ii-action-icon amber">{icon("table", 20)}</div>'
            f'<div class="ii-action-title">'
            f'{escape(t("Populated sample file"))}</div>'
            '<p class="ii-action-text">'
            f"{escape(t('Download the same dataset as an Excel file to inspect it, change it and upload it again.'))}"
            "</p>",
            unsafe_allow_html=True,
        )

        scenario = _scenario_picker(SAMPLE_DOWNLOAD_KEY, label=t("File to download"))

        try:
            payload = cached_sample_workbook_bytes(scenario.key)
        except Exception:  # pragma: no cover - defensive guard
            logger.exception("Could not generate the sample workbook")
            st.error(t("The sample workbook could not be generated."))
            return

        st.download_button(
            t("📊 Download sample data"),
            data=payload,
            file_name=sample_filename(scenario.key),
            mime=_XLSX_MIME,
            type="secondary",
            width="stretch",
            icon=":material/download:",
            key="download_sample_data",
            help=t(
                "The downloaded file validates against the same rules as your "
                "own upload."
            ),
        )


def _scenario_picker(key: str, *, label: str):
    """Render a scenario selector and return the selected scenario."""

    labels = [t(scenario.name) for scenario in SAMPLE_SCENARIOS]
    keys = [scenario.key for scenario in SAMPLE_SCENARIOS]

    stored = st.session_state.get(key)
    index = keys.index(stored) if stored in keys else keys.index(DEFAULT_SCENARIO_KEY)

    selected = st.selectbox(
        label,
        labels,
        index=index,
        key=f"{key}_widget",
        label_visibility="collapsed",
        help=t("Each scenario is built to trigger a different set of warnings."),
    )

    chosen = SAMPLE_SCENARIOS[labels.index(selected)]
    st.session_state[key] = chosen.key
    return chosen


def _activate_scenario(key: str) -> None:
    """Load a generated scenario into state and open the dashboard."""

    result = load_sample_dataset(key)
    if result.is_valid and result.dataset is not None:
        st.session_state.pop(SAMPLE_ERROR_KEY, None)
        reset_upload_state()
        set_page(PAGE_OVERVIEW)
        st.rerun()
        return

    logger.warning(
        "Sample scenario '%s' failed validation: %s",
        key,
        [issue.code for issue in result.issues],
    )
    st.session_state[SAMPLE_ERROR_KEY] = result


__all__ = [
    "SAMPLE_ERROR_KEY",
    "SAMPLE_SELECT_KEY",
    "render_quick_start",
]
