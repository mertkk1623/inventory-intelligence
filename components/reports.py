"""Reports screen: download the Excel workbook and the PDF report.

The screen is a thin presentation layer. It never calculates inventory values
itself; it builds a :class:`reports.ReportContext` from the shared calculation
object and hands it to the report builders.

Report files are always generated in English. The interface states that scope
explicitly so a Turkish interface never implies a Turkish workbook.
"""

from __future__ import annotations

import logging
from html import escape

import streamlit as st

from components.analytics_ui import format_date, format_quantity, page_header
from components.ui import banner, icon
from reports import build_report_context
from reports.excel_report import build_excel_report
from reports.pdf_report import build_pdf_report
from reports.report_data import ReportContext
from utils.i18n import format_number, t

logger = logging.getLogger(__name__)

EXCEL_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
PDF_MIME = "application/pdf"

EXCEL_SHEETS: tuple[tuple[str, str], ...] = (
    (
        "Executive Summary",
        "Product, stock, consumption and replenishment values on one page.",
    ),
    (
        "Stock Movements",
        "Every IN and OUT movement in range with its closing balance.",
    ),
    (
        "Consumption Analysis",
        "Average, total, highest and lowest day plus daily and weekly series.",
    ),
    (
        "Replenishment Plan",
        "Planning thresholds, inventory position and the suggested order.",
    ),
    (
        "Open Purchase Orders",
        "Order quantity, expected delivery date and overdue status.",
    ),
)

PDF_SECTIONS: tuple[tuple[str, str], ...] = (
    ("Report header", "Product, report date and generation date."),
    ("Executive summary", "Current stock, consumption, supply and suggested order."),
    ("Stock analysis", "Opening and current stock, IN/OUT totals and balance trend."),
    ("Consumption analysis", "Daily and weekly charts with the consumption summary."),
    ("Replenishment planning", "Thresholds, inventory position and reorder status."),
    ("Open purchase orders", "Delivery schedule and overdue status."),
    ("Methodology & notes", "Formulas, report window and reporting limitations."),
)

# Report _files_ are English-only: sheet names, section headings, labels and
# note text all come from the report builders. Only this screen's descriptive
# copy is translated, and sheet/section names stay in English so the screen
# matches the file the user downloads.


def render_reports(dataset, calculation) -> None:
    """Render the report download screen for the active dataset."""

    st.markdown(
        page_header(
            t("Reports"),
            t(
                "Download a formatted Excel workbook or a presentation-ready "
                "PDF for the selected report date. Both files are generated "
                "from the same calculation result."
            ),
            dataset,
            as_of=calculation.report_date,
        ),
        unsafe_allow_html=True,
    )

    try:
        context = build_report_context(dataset, calculation)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Could not prepare the report context")
        st.error(
            t(
                "The report could not be prepared for this dataset and report "
                "date. Details: {error}",
                error=exc,
            )
        )
        return

    st.markdown(_context_strip(context), unsafe_allow_html=True)

    if context.is_historical:
        st.markdown(
            banner(
                "warning",
                t("Historical report date"),
                t(
                    "Replenishment planning is supported only for the current "
                    "report date. This report keeps the stock and consumption "
                    "history up to {date} and explains the planning limitation "
                    "instead of showing order suggestions.",
                    date=format_date(context.report_date),
                ),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="ii-report-grid">'
        f"{_report_card('excel')}"
        f"{_report_card('pdf')}"
        "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="medium")
    with left:
        _excel_download(context)
    with right:
        _pdf_download(context)

    st.markdown(
        '<div class="ii-report-note">'
        f"<strong>{t('Report language')}.</strong> "
        f"{t('Excel and PDF files are generated in English for both interface languages. Dashboard values and the interface follow the selected language.')}"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ii-report-note">'
        f"<strong>{t('Static snapshots.')}</strong> "
        f"{t('Reports are built from the workbook currently loaded in the workspace. Changing the report date in the sidebar regenerates both files with a new date, so the download always matches what the dashboard shows.')}"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Download buttons
# ---------------------------------------------------------------------------


def _excel_download(context: ReportContext) -> None:
    key = f"download_excel_{context.file_stem}"
    try:
        payload = build_excel_report(context)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Excel report generation failed")
        st.error(
            t(
                "The Excel report could not be generated. Details: {error}",
                error=exc,
            )
        )
        return

    st.download_button(
        t("Download Excel Report"),
        data=payload,
        file_name=f"{context.file_stem}.xlsx",
        mime=EXCEL_MIME,
        type="primary",
        icon=":material/download:",
        width="stretch",
        key=key,
    )


def _pdf_download(context: ReportContext) -> None:
    key = f"download_pdf_{context.file_stem}"
    try:
        payload = build_pdf_report(context)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("PDF report generation failed")
        st.error(
            t(
                "The PDF report could not be generated. Details: {error}",
                error=exc,
            )
        )
        return

    st.download_button(
        t("Download PDF Report"),
        data=payload,
        file_name=f"{context.file_stem}.pdf",
        mime=PDF_MIME,
        type="primary",
        icon=":material/picture_as_pdf:",
        width="stretch",
        key=key,
    )


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _context_strip(context: ReportContext) -> str:
    calculation = context.calculation
    chips = [
        t("Report date {date}", date=format_date(context.report_date)),
        t("Current report" if not context.is_historical else "Historical report"),
        t(
            "Current stock {quantity}",
            quantity=format_quantity(calculation.current_stock, context.unit),
        ),
        t(
            "{count} movements in range",
            count=format_number(len(context.movement_rows())),
        ),
    ]
    return (
        '<div class="ii-report-meta">'
        + "".join(f"<span>{chip}</span>" for chip in chips)
        + "</div>"
    )


def _report_card(kind: str) -> str:
    if kind == "excel":
        icon_name = "table"
        kicker = t("Spreadsheet")
        name = t("Excel Report")
        description = t(
            "A structured workbook for analysis and sharing. Five sheets cover "
            "the executive summary, every movement, consumption detail, the "
            "replenishment plan and open purchase orders. Values are static so "
            "the file matches the calculation engine exactly."
        )
        items = EXCEL_SHEETS
        numbered = True
        footer = t(
            "Frozen header rows, filters on table sheets, consistent date and "
            "number formats. No formulas; every value is written by Python."
        )
        list_label = t("Sheets included")
    else:
        icon_name = "sheet"
        kicker = t("Document")
        name = t("PDF Report")
        description = t(
            "A presentation-ready A4 document for management review. Seven "
            "sections combine the key position, a stock balance trend and the "
            "consumption charts with the planning methodology behind them."
        )
        items = PDF_SECTIONS
        numbered = True
        footer = t(
            "A4 portrait, navy and primary blue, numbered pages and charts "
            "drawn from the same series as the dashboard."
        )
        list_label = t("Sections included")

    rows = []
    for index, (title, detail) in enumerate(items, start=1):
        marker = (
            f'<span class="num">{index:02d}</span>'
            if numbered
            else f'<span class="tick">{icon("check", 12)}</span>'
        )
        rows.append(
            f"<li>{marker}<span><strong>{escape(title)}</strong> — "
            f"{escape(t(detail))}</span></li>"
        )

    icon_class = "ii-report-icon pdf" if kind == "pdf" else "ii-report-icon"
    return (
        '<div class="ii-report-card">'
        '<div class="ii-report-top">'
        f'<div class="{icon_class}">{icon(icon_name, 20)}</div>'
        "<div>"
        f'<div class="ii-report-kicker">{kicker}</div>'
        f'<div class="ii-report-name">{name}</div>'
        "</div>"
        "</div>"
        f'<p class="ii-report-desc">{description}</p>'
        f'<div class="ii-report-list-label">{list_label}</div>'
        f'<ul class="ii-report-items">{"".join(rows)}</ul>'
        f'<div class="ii-report-foot">{footer}</div>'
        "</div>"
    )
