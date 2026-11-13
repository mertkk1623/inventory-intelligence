"""Stock Analysis screen: movement history, filters and balance trend."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from analytics.series import (
    filter_movements,
    movement_totals,
    stock_balance_series,
)
from components.analytics_ui import (
    KpiItem,
    card_header,
    chart,
    empty_state,
    format_date,
    format_quantity,
    kpi_cards,
    page_header,
)
from components.charts import stock_level_figure
from components.ui import banner
from core.inventory import TRANSACTION_IN, TRANSACTION_OUT
from core.models import InventoryCalculation, InventoryDataset
from utils.i18n import (
    format_number,
    localise_columns,
    t,
    table_date_format,
)


def render_stock_analysis(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    """Render stock KPIs, a prioritised movement table and a balance chart."""

    product = dataset.product
    st.markdown(
        page_header(
            t("Stock Analysis"),
            t(
                "Review every IN and OUT movement, then inspect how the "
                "balance developed through the report date."
            ),
            dataset,
            as_of=calculation.report_date,
        ),
        unsafe_allow_html=True,
    )

    if calculation.negative_stock_warning:
        st.markdown(
            banner(
                "error",
                t("Negative stock detected"),
                t(
                    "Lowest running balance: {balance} {unit}. The balance is "
                    "not clamped to zero.",
                    balance=format_number(calculation.lowest_stock_balance),
                    unit=product.unit,
                ),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Opening Stock"),
                    format_quantity(product.opening_stock, product.unit),
                    t(
                        "As of {date}",
                        date=format_date(product.opening_stock_date),
                    ),
                ),
                KpiItem(
                    t("Current Stock"),
                    format_quantity(calculation.current_stock, product.unit),
                    t("At {date}", date=format_date(calculation.report_date)),
                    "critical" if calculation.negative_stock_warning else "",
                ),
                KpiItem(
                    t("Total IN"),
                    format_quantity(calculation.total_in, product.unit),
                    t("Up to the report date"),
                    "success",
                ),
                KpiItem(
                    t("Total OUT"),
                    format_quantity(calculation.total_out, product.unit),
                    t("Up to the report date"),
                    "warning",
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    start, end, transaction_types = _render_filters(dataset, calculation)

    movements = filter_movements(dataset, start, end, transaction_types)
    filtered_in, filtered_out = movement_totals(movements)

    st.markdown(
        card_header(
            t("Stock Movement History"),
            t(
                "Newest movements first. Use the filters above to narrow the "
                "list."
            ),
        ),
        unsafe_allow_html=True,
    )

    if movements:
        st.caption(
            t(
                "{count} movements · IN {inbound} · OUT {outbound} {unit}"
                if len(movements) != 1
                else "{count} movement · IN {inbound} · OUT {outbound} {unit}",
                count=len(movements),
                inbound=format_number(filtered_in),
                outbound=format_number(filtered_out),
                unit=product.unit,
            )
        )
        columns = {
            "Date": t("Date"),
            "Transaction Type": t("Transaction Type"),
            "Quantity": t("Quantity"),
            "Description": t("Description"),
        }
        frame = pd.DataFrame(
            [
                {
                    columns["Date"]: movement.date,
                    columns["Transaction Type"]: movement.transaction_type,
                    columns["Quantity"]: movement.quantity,
                    columns["Description"]: movement.description,
                }
                for movement in movements
            ]
        )
        frame = localise_columns(frame, {columns["Quantity"]: 0})
        st.dataframe(
            frame,
            hide_index=True,
            width="stretch",
            height=min(430, 40 + 35 * len(movements)),
            column_config={
                columns["Date"]: st.column_config.DateColumn(
                    columns["Date"], format=table_date_format()
                ),
                columns["Transaction Type"]: st.column_config.TextColumn(
                    columns["Transaction Type"], width="small"
                ),
                columns["Quantity"]: st.column_config.NumberColumn(
                    columns["Quantity"], format="%d", width="small"
                ),
            },
        )
    else:
        empty_state(
            t("No movements match these filters"),
            t("Adjust the date range or include IN and OUT movements."),
        )

    st.markdown(
        card_header(
            t("Stock Balance Trend"),
            t(
                "The balance always includes both IN and OUT movements, even "
                "when the history table is filtered to one direction."
            ),
        ),
        unsafe_allow_html=True,
    )

    points = tuple(
        point
        for point in stock_balance_series(dataset, calculation.report_date)
        if start <= point[0] <= end
    )
    if not points:
        empty_state(
            t("No balance points in this range"),
            t("Choose a date range within the dataset history."),
        )
        return

    balance_by_day = {day: balance for day, balance in points}
    markers = tuple(
        (
            movement.date,
            balance_by_day.get(movement.date, calculation.current_stock),
            movement.transaction_type,
            movement.quantity,
            movement.description or t("No description"),
        )
        for movement in movements
    )

    with st.container(border=True):
        chart(
            stock_level_figure(
                points,
                calculation,
                height=320,
                movement_markers=markers,
            ),
            key="stock_balance_trend",
        )


def _render_filters(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> tuple[date, date, tuple[str, ...]]:
    product = dataset.product
    lower = product.opening_stock_date
    upper = calculation.report_date
    date_suffix = calculation.report_date.isoformat()
    date_format = table_date_format()

    with st.container(border=True):
        st.markdown(
            card_header(
                t("Movement filters"),
                t("Dates are limited to the validated dataset history."),
            ),
            unsafe_allow_html=True,
        )
        date_column, type_column = st.columns([2, 1], gap="large")
        with date_column:
            start_col, end_col = st.columns(2, gap="medium")
            with start_col:
                start = st.date_input(
                    t("From"),
                    value=lower,
                    min_value=lower,
                    max_value=upper,
                    format=date_format,
                    key=f"stock_from_{date_suffix}",
                )
            with end_col:
                end = st.date_input(
                    t("To"),
                    value=upper,
                    min_value=lower,
                    max_value=upper,
                    format=date_format,
                    key=f"stock_to_{date_suffix}",
                )
        with type_column:
            selected = st.multiselect(
                t("Transaction type"),
                options=[TRANSACTION_IN, TRANSACTION_OUT],
                default=[TRANSACTION_IN, TRANSACTION_OUT],
                key="stock_movement_types",
            )

    start_date = start if isinstance(start, date) else lower
    end_date = end if isinstance(end, date) else upper
    if start_date > end_date:
        st.warning(
            t(
                "The start date is after the end date. The range has been "
                "reversed for this view."
            )
        )
        start_date, end_date = end_date, start_date

    return start_date, end_date, tuple(selected)
