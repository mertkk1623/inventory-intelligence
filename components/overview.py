"""Overview Dashboard built from real calculation results."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.series import (
    daily_consumption_series,
    open_order_rows,
    stock_balance_series,
    stock_status_label,
)
from components.analytics_ui import (
    KpiItem,
    card_header,
    chart,
    empty_state,
    format_days,
    format_decimal,
    format_quantity,
    kpi_cards,
    page_header,
)
from components.charts import (
    daily_consumption_figure,
    safety_vs_reorder_figure,
    stock_level_figure,
)
from components.ui import banner
from core.models import InventoryCalculation, InventoryDataset
from utils.i18n import (
    format_number,
    localise_columns,
    t,
    table_date_format,
)


def render_dashboard(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    """Render the Overview Dashboard from the shared calculation result."""

    product = dataset.product
    st.markdown(
        page_header(
            t("Overview Dashboard"),
            t(
                "{code} · {name} · {unit} planning workspace.",
                code=product.product_code,
                name=product.product_name,
                unit=product.unit,
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
                    "The running balance dropped below zero at some point up to "
                    "the report date. Lowest balance: {balance} {unit}.",
                    balance=format_number(calculation.lowest_stock_balance),
                    unit=product.unit,
                ),
            ),
            unsafe_allow_html=True,
        )

    if calculation.is_historical_report:
        st.markdown(
            banner(
                "info",
                t("Historical report"),
                t(calculation.replenishment_note),
            ),
            unsafe_allow_html=True,
        )
    elif calculation.reorder_required:
        st.markdown(
            banner(
                "warning",
                t("Reorder required"),
                t(
                    "Inventory position is at or below the reorder point. "
                    "Suggested order quantity: {quantity} {unit}.",
                    quantity=format_number(calculation.suggested_order_quantity),
                    unit=product.unit,
                ),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Current Stock"),
                    format_quantity(calculation.current_stock, product.unit),
                    t(
                        "Opening {opening} · IN {inbound} · OUT {outbound}",
                        opening=format_number(product.opening_stock),
                        inbound=format_number(calculation.total_in),
                        outbound=format_number(calculation.total_out),
                    ),
                    "critical" if calculation.negative_stock_warning else "",
                ),
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
                ),
                KpiItem(
                    t("Days of Supply"),
                    format_days(calculation.days_of_supply),
                    t("No consumption in the window")
                    if calculation.days_of_supply is None
                    else t("At the current consumption rate"),
                    "warning" if calculation.days_of_supply is None else "",
                ),
                KpiItem(
                    t("Suggested Order Quantity"),
                    "—"
                    if not calculation.replenishment_supported
                    else format_quantity(
                        calculation.suggested_order_quantity, product.unit
                    ),
                    t("Not generated for historical reports")
                    if not calculation.replenishment_supported
                    else (
                        t("Reorder required")
                        if calculation.reorder_required
                        else t("No reorder required")
                    ),
                    "warning"
                    if calculation.replenishment_supported
                    and calculation.reorder_required
                    else "muted"
                    if not calculation.replenishment_supported
                    else "success",
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    balance_points = stock_balance_series(dataset, calculation.report_date)
    daily = daily_consumption_series(dataset, calculation.report_date)

    left, right = st.columns([1.7, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown(
                card_header(
                    t("Stock Level Trend"),
                    t(
                        "Daily closing balance with safety stock and reorder "
                        "point."
                    ),
                ),
                unsafe_allow_html=True,
            )
            chart(
                stock_level_figure(balance_points, calculation),
                key="dashboard_stock_trend",
            )

    with right:
        with st.container(border=True):
            st.markdown(
                card_header(
                    t("Safety Stock vs Reorder Point"),
                    t("Current stock is shown as a reference line."),
                ),
                unsafe_allow_html=True,
            )
            chart(
                safety_vs_reorder_figure(calculation),
                key="dashboard_safety_reorder",
            )

    with st.container(border=True):
        st.markdown(
            card_header(
                t("Daily Consumption Trend"),
                t(
                    "OUT movements in the rolling consumption window. Days "
                    "without consumption are shown as zero."
                ),
            ),
            unsafe_allow_html=True,
        )
        chart(
            daily_consumption_figure(daily),
            key="dashboard_daily_consumption",
        )

    st.markdown(
        card_header(
            t("Stock Status"),
            t("Current stock, planning thresholds and stock health."),
        ),
        unsafe_allow_html=True,
    )
    _render_stock_status(dataset, calculation)

    st.markdown(
        card_header(
            t("Open Purchase Orders"),
            t("Purchase orders awaiting delivery."),
        ),
        unsafe_allow_html=True,
    )
    _render_open_orders(dataset, calculation)


def _render_stock_status(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    product = dataset.product
    status = t(stock_status_label(calculation))
    columns = {
        "Product Code": t("Product Code"),
        "Product": t("Product Name"),
        "Unit": t("Unit"),
        "Current Stock": t("Current Stock"),
        "Safety Stock": t("Safety Stock"),
        "Reorder Point": t("Reorder Point"),
        "Days of Supply": t("Days of Supply"),
        "Status": t("Status"),
    }
    frame = pd.DataFrame(
        [
            {
                columns["Product Code"]: product.product_code,
                columns["Product"]: product.product_name,
                columns["Unit"]: product.unit,
                columns["Current Stock"]: calculation.current_stock,
                columns["Safety Stock"]: calculation.safety_stock,
                columns["Reorder Point"]: float(calculation.reorder_point),
                columns["Days of Supply"]: (
                    float(calculation.days_of_supply)
                    if calculation.days_of_supply is not None
                    else None
                ),
                columns["Status"]: status,
            }
        ]
    )
    # Turkish reads "212,4"; Streamlit's NumberColumn is always English, so the
    # display columns are locale-formatted text in Turkish only. English keeps
    # numeric dtypes so the table stays sortable.
    frame = localise_columns(
        frame,
        {
            columns["Current Stock"]: 0,
            columns["Safety Stock"]: 0,
            columns["Reorder Point"]: 1,
            columns["Days of Supply"]: 1,
        },
    )
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        column_config={
            columns["Current Stock"]: st.column_config.NumberColumn(
                columns["Current Stock"], format="%d"
            ),
            columns["Safety Stock"]: st.column_config.NumberColumn(
                columns["Safety Stock"], format="%d"
            ),
            columns["Reorder Point"]: st.column_config.NumberColumn(
                columns["Reorder Point"], format="%.1f"
            ),
            columns["Days of Supply"]: st.column_config.NumberColumn(
                columns["Days of Supply"], format="%.1f"
            ),
            columns["Status"]: st.column_config.TextColumn(columns["Status"]),
        },
    )


def _render_open_orders(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    rows = open_order_rows(dataset, calculation.report_date)
    if not rows:
        empty_state(
            t("No open purchase orders"),
            t("This workbook contains no incoming purchase orders."),
        )
        return

    if calculation.is_historical_report:
        st.markdown(
            banner(
                "info",
                t("Current open orders are not included"),
                t(
                    "These orders are shown for reference only. Historical "
                    "reports exclude current open orders from Inventory "
                    "Position."
                ),
            ),
            unsafe_allow_html=True,
        )

    columns = {
        "Order No": t("Order No"),
        "Order Quantity": t("Order Quantity"),
        "Expected Delivery Date": t("Expected Delivery Date"),
        "Status": t("Status"),
    }
    frame = pd.DataFrame(
        [
            {
                columns["Order No"]: row.order.order_no,
                columns["Order Quantity"]: row.order.order_quantity,
                columns["Expected Delivery Date"]: row.order.expected_delivery_date,
                columns["Status"]: (
                    t("Not included")
                    if calculation.is_historical_report
                    else t("Overdue")
                    if row.is_overdue
                    else t("Scheduled")
                ),
            }
            for row in rows
        ]
    )
    frame = localise_columns(frame, {columns["Order Quantity"]: 0})
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        column_config={
            columns["Order Quantity"]: st.column_config.NumberColumn(
                columns["Order Quantity"], format="%d"
            ),
            columns["Expected Delivery Date"]: st.column_config.DateColumn(
                columns["Expected Delivery Date"], format=table_date_format()
            ),
        },
    )
    st.caption(
        t(
            "Total open order quantity: {quantity} {unit}.",
            quantity=format_number(
                sum(row.order.order_quantity for row in rows)
            ),
            unit=dataset.product.unit,
        )
    )


# The old page name remains available for callers that still use it.
render_overview = render_dashboard
