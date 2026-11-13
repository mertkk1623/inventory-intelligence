"""Consumption Analysis screen with zero-filled daily and weekly charts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.series import (
    consumption_summary,
    daily_consumption_series,
    weekly_consumption_series,
)
from components.analytics_ui import (
    KpiItem,
    card_header,
    chart,
    empty_state,
    format_date,
    format_decimal,
    format_quantity,
    kpi_cards,
    page_header,
)
from components.charts import daily_consumption_figure, weekly_consumption_figure
from components.ui import banner
from core.models import InventoryCalculation, InventoryDataset
from utils.i18n import localise_columns, t, table_date_format


def render_consumption_analysis(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    """Render consumption KPIs and zero-filled daily/weekly charts."""

    product = dataset.product
    st.markdown(
        page_header(
            t("Consumption Analysis"),
            t(
                "Understand OUT consumption in the rolling calculation window. "
                "Days without movements remain visible as zero."
            ),
            dataset,
            as_of=calculation.report_date,
        ),
        unsafe_allow_html=True,
    )

    daily = daily_consumption_series(dataset, calculation.report_date)
    summary = consumption_summary(daily)
    weekly = weekly_consumption_series(daily)

    if not daily:
        empty_state(
            t("No consumption window"),
            t(
                "The report date does not provide a consumption window for "
                "this dataset."
            ),
        )
        return

    window_text = (
        f"{format_date(daily[0].day)} – {format_date(daily[-1].day)}"
        if daily
        else "—"
    )

    if summary.total == 0:
        st.markdown(
            banner(
                "info",
                t("No consumption recorded"),
                t(
                    "There are no OUT movements in the consumption window. "
                    "Average daily consumption is zero and every day is shown "
                    "as zero."
                ),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Average Daily Consumption"),
                    format_decimal(
                        calculation.average_daily_consumption,
                        t("{unit}/day", unit=product.unit),
                        places=2,
                    ),
                    t(
                        "{days} calendar days covered",
                        days=calculation.consumption_coverage_days,
                    ),
                    "muted" if summary.total == 0 else "",
                ),
                KpiItem(
                    t("Total Consumption"),
                    format_quantity(summary.total, product.unit),
                    t("Window {window}", window=window_text),
                    "muted" if summary.total == 0 else "",
                ),
                KpiItem(
                    t("Highest Consumption Day"),
                    t("No consumption")
                    if summary.total == 0
                    else format_quantity(summary.highest_quantity, product.unit),
                    t("No OUT movements in the window")
                    if summary.total == 0
                    else format_date(summary.highest_day),
                    "muted" if summary.total == 0 else "success",
                ),
                KpiItem(
                    t("Lowest Consumption Day"),
                    format_quantity(summary.lowest_quantity, product.unit),
                    format_date(summary.lowest_day)
                    if summary.total > 0
                    else t("Zero-consumption days included"),
                    "muted",
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            card_header(
                t("Daily Consumption"),
                t(
                    "OUT units per calendar day. Missing days are explicitly "
                    "zero."
                ),
            ),
            unsafe_allow_html=True,
        )
        chart(
            daily_consumption_figure(daily, height=300),
            key="consumption_daily_chart",
        )

    with st.container(border=True):
        st.markdown(
            card_header(
                t("Weekly Consumption"),
                t("Monday-based weekly totals across the consumption window."),
            ),
            unsafe_allow_html=True,
        )
        chart(
            weekly_consumption_figure(weekly, height=300),
            key="consumption_weekly_chart",
        )

    with st.expander(t("Daily consumption values"), expanded=False):
        columns = {"Date": t("Date"), "Consumption": t("Consumption")}
        frame = pd.DataFrame(
            [
                {
                    columns["Date"]: entry.day,
                    columns["Consumption"]: entry.quantity,
                }
                for entry in daily
            ]
        )
        frame = localise_columns(frame, {columns["Consumption"]: 0})
        st.dataframe(
            frame,
            hide_index=True,
            width="stretch",
            height=min(360, 40 + 32 * len(daily)),
            column_config={
                columns["Date"]: st.column_config.DateColumn(
                    columns["Date"], format=table_date_format()
                ),
                columns["Consumption"]: st.column_config.NumberColumn(
                    columns["Consumption"], format="%d"
                ),
            },
        )
