"""Replenishment Planning screen built on the calculation engine result."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics.series import open_order_rows
from components.analytics_ui import (
    KpiItem,
    card_header,
    empty_state,
    format_decimal,
    format_quantity,
    kpi_cards,
    page_header,
)
from components.ui import banner
from core.models import InventoryCalculation, InventoryDataset
from utils.i18n import (
    format_number,
    localise_columns,
    t,
    table_date_format,
)


def render_replenishment(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    """Render replenishment metrics, status and open purchase orders."""

    product = dataset.product
    st.markdown(
        page_header(
            t("Replenishment Planning"),
            t(
                "Compare stock, open supply and planning thresholds to decide "
                "whether a new purchase order is needed."
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
                    "Lowest running balance: {balance} {unit}. The planning "
                    "values below use the unclamped current stock.",
                    balance=format_number(calculation.lowest_stock_balance),
                    unit=product.unit,
                ),
            ),
            unsafe_allow_html=True,
        )

    reorder_point = format_number(
        round(float(calculation.reorder_point), 1), places=1
    )
    position = format_number(calculation.inventory_position)
    suggested = format_number(calculation.suggested_order_quantity)

    if not calculation.replenishment_supported:
        st.markdown(
            banner(
                "info",
                t("Historical report limitation"),
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
                    "Inventory position ({position} {unit}) is at or below the "
                    "reorder point ({point} {unit}). Suggested order quantity: "
                    "{quantity} {unit}.",
                    position=position,
                    point=reorder_point,
                    quantity=suggested,
                    unit=product.unit,
                ),
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            banner(
                "success",
                t("No reorder required"),
                t(
                    "Inventory position ({position} {unit}) is above the "
                    "reorder point ({point} {unit}).",
                    position=position,
                    point=reorder_point,
                    unit=product.unit,
                ),
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Reorder Point"),
                    format_decimal(calculation.reorder_point, product.unit, places=1),
                    t("Average consumption × lead time + safety stock"),
                ),
                KpiItem(
                    t("Safety Stock"),
                    format_quantity(calculation.safety_stock, product.unit),
                    t("Minimum planning buffer"),
                ),
                KpiItem(
                    t("Lead Time"),
                    t("{days} days", days=calculation.lead_time_days),
                    t("Expected supplier lead time"),
                ),
                KpiItem(
                    t("Current Stock"),
                    format_quantity(calculation.current_stock, product.unit),
                    t("Open orders are not added to stock"),
                    "critical" if calculation.negative_stock_warning else "",
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Open Order Quantity"),
                    "—"
                    if not calculation.replenishment_supported
                    else format_quantity(
                        calculation.total_open_order_quantity, product.unit
                    ),
                    t("Excluded from historical inventory position")
                    if not calculation.replenishment_supported
                    else t("All open orders are included"),
                    "muted" if not calculation.replenishment_supported else "",
                ),
                KpiItem(
                    t("Inventory Position"),
                    format_quantity(calculation.inventory_position, product.unit),
                    t("Current stock + all open orders")
                    if calculation.replenishment_supported
                    else t("Current stock only (historical report)"),
                ),
                KpiItem(
                    t("Target Stock"),
                    format_decimal(calculation.target_stock, product.unit, places=1),
                    t("Average consumption × (lead + coverage) + safety stock"),
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
                        t("Order up to target stock")
                        if calculation.reorder_required
                        else t("No reorder required")
                    ),
                    "muted"
                    if not calculation.replenishment_supported
                    else "warning"
                    if calculation.reorder_required
                    else "success",
                ),
            )
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        kpi_cards(
            (
                KpiItem(
                    t("Reorder Required"),
                    t("Yes")
                    if calculation.replenishment_supported
                    and calculation.reorder_required
                    else t("No")
                    if calculation.replenishment_supported
                    else t("Not supported"),
                    t("Inventory position is at or below the reorder point")
                    if calculation.replenishment_supported
                    and calculation.reorder_required
                    else t("Inventory position is above the reorder point")
                    if calculation.replenishment_supported
                    else t("Historical report"),
                    "warning"
                    if calculation.replenishment_supported
                    and calculation.reorder_required
                    else "muted"
                    if not calculation.replenishment_supported
                    else "success",
                ),
                KpiItem(
                    t("Overdue Orders"),
                    "—"
                    if not calculation.replenishment_supported
                    else format_number(calculation.overdue_order_count),
                    t("Not evaluated for historical reports")
                    if not calculation.replenishment_supported
                    else t("Expected delivery date before the report date"),
                    "muted"
                    if not calculation.replenishment_supported
                    else "warning"
                    if calculation.overdue_order_count
                    else "success",
                ),
            ),
            columns=2,
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        banner(
            "info",
            t("How Inventory Position works"),
            t(
                "Inventory Position = Current Stock + all open order quantities. "
                "Open orders are treated as incoming supply and are never added "
                "to Current Stock."
            ),
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        card_header(
            t("Open Purchase Orders"),
            t("Order number, quantity and expected delivery date."),
        ),
        unsafe_allow_html=True,
    )
    _render_open_orders(dataset, calculation)


def _render_open_orders(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> None:
    rows = open_order_rows(dataset, calculation.report_date)
    if not rows:
        empty_state(
            t("No open purchase orders"),
            t("Inventory Position therefore equals Current Stock."),
        )
        return

    if not calculation.replenishment_supported:
        st.markdown(
            banner(
                "info",
                t("Reference only"),
                t(
                    "Current open orders are shown for reference but are "
                    "excluded from this historical report's Inventory Position."
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
                    if not calculation.replenishment_supported
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
            "{count} open orders · Total quantity {quantity} {unit}."
            if len(rows) != 1
            else "{count} open order · Total quantity {quantity} {unit}.",
            count=len(rows),
            quantity=format_number(
                sum(row.order.order_quantity for row in rows)
            ),
            unit=dataset.product.unit,
        )
    )
