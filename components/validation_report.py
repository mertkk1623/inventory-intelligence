"""Render workbook validation results in a clear, non-technical way."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.ui import banner
from core.validation import ValidationIssue, ValidationResult
from utils.i18n import t, translate_message


def render_validation_result(result: ValidationResult) -> None:
    """Show errors and warnings for a workbook that could not be loaded."""

    errors = result.errors
    warnings = result.warnings

    if errors:
        st.markdown(
            banner(
                "error",
                t(
                    "{count} issues found in {filename}"
                    if len(errors) != 1
                    else "{count} issue found in {filename}",
                    count=len(errors),
                    filename=result.filename,
                ),
                t(
                    "The workbook was not loaded. Fix the items below and upload "
                    "the file again."
                ),
            ),
            unsafe_allow_html=True,
        )
        _render_issue_table(errors)
        if any(issue.code == "missing_sheet" for issue in errors):
            st.caption(
                t(
                    "Worksheets found in this file: {sheets}",
                    sheets=", ".join(result.sheets_found),
                )
            )
    elif result.is_valid:
        st.markdown(
            banner(
                "success",
                t("Workbook validated successfully"),
                t(
                    "{filename} passed every validation rule.",
                    filename=result.filename,
                ),
            ),
            unsafe_allow_html=True,
        )

    if warnings:
        if errors:
            with st.expander(
                t("Warnings ({count})", count=len(warnings)), expanded=False
            ):
                _render_issue_table(warnings)
        else:
            st.markdown(
                banner(
                    "warning",
                    t(
                        "Workbook loaded with {count} warnings"
                        if len(warnings) != 1
                        else "Workbook loaded with {count} warning",
                        count=len(warnings),
                    ),
                    t("The dataset is usable, but review the notes below."),
                ),
                unsafe_allow_html=True,
            )
            with st.expander(t("Review warnings"), expanded=False):
                _render_issue_table(warnings)


def _render_issue_table(issues: list[ValidationIssue]) -> None:
    rows = [
        {
            "severity": t("Error") if issue.severity == "error" else t("Warning"),
            "sheet": issue.sheet or t("Workbook"),
            "row": str(issue.row) if issue.row is not None else "—",
            "column": issue.column or "—",
            "issue": translate_message(issue.message),
        }
        for issue in issues
    ]
    frame = pd.DataFrame(rows).rename(
        columns={
            "severity": t("Severity"),
            "sheet": t("Sheet"),
            "row": t("Excel Row"),
            "column": t("Column"),
            "issue": t("Issue"),
        }
    )
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        column_config={
            t("Severity"): st.column_config.TextColumn(t("Severity"), width="small"),
            t("Sheet"): st.column_config.TextColumn(t("Sheet"), width="medium"),
            t("Excel Row"): st.column_config.TextColumn(
                t("Excel Row"), width="small"
            ),
            t("Column"): st.column_config.TextColumn(t("Column"), width="medium"),
            t("Issue"): st.column_config.TextColumn(t("Issue"), width="large"),
        },
    )
    st.caption(
        t("Excel Row refers to the row number in the original worksheet.")
    )
