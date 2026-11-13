"""Replenishment planning formulas for the single-SKU workspace.

Open orders are supply, not stock. They are therefore only added when
calculating inventory position and are never folded into current stock.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from math import ceil

from core.inventory import as_date, require_whole_number
from core.models import OpenOrder


def calculate_reorder_point(
    average_daily_consumption: Decimal,
    lead_time_days: int,
    safety_stock: int,
) -> Decimal:
    """Reorder Point = average consumption × lead time + safety stock."""

    lead_days = require_whole_number(
        lead_time_days, "Lead Time Days", minimum=0
    )
    safety = require_whole_number(safety_stock, "Safety Stock", minimum=0)

    return (
        average_daily_consumption * Decimal(lead_days) + Decimal(safety)
    )


def calculate_target_stock(
    average_daily_consumption: Decimal,
    lead_time_days: int,
    target_coverage_days: int,
    safety_stock: int,
) -> Decimal:
    """Target Stock = average consumption × (lead + coverage) + safety stock."""

    lead_days = require_whole_number(
        lead_time_days, "Lead Time Days", minimum=0
    )
    coverage_days = require_whole_number(
        target_coverage_days, "Target Coverage Days", minimum=1
    )
    safety = require_whole_number(safety_stock, "Safety Stock", minimum=0)

    coverage = lead_days + coverage_days
    return (
        average_daily_consumption * Decimal(coverage) + Decimal(safety)
    )


def calculate_inventory_position(
    current_stock: int,
    open_orders: Iterable[OpenOrder],
) -> int:
    """Inventory Position = current stock + all valid open order quantities."""

    position = require_whole_number(current_stock, "Current Stock")
    for order in open_orders:
        position += require_whole_number(
            order.order_quantity, "Order Quantity", minimum=1
        )
    return position


def count_overdue_orders(
    open_orders: Iterable[OpenOrder],
    report_date,
) -> int:
    """Count open orders whose expected delivery date is before the report date."""

    report = as_date(report_date, "report date")
    return sum(
        1
        for order in open_orders
        if as_date(order.expected_delivery_date, "expected delivery date") < report
    )


def is_reorder_required(
    inventory_position: int,
    reorder_point: Decimal,
) -> bool:
    """The reorder condition is inclusive: position <= reorder point."""

    position = require_whole_number(inventory_position, "Inventory Position")
    return position <= reorder_point


def calculate_suggested_order_quantity(
    inventory_position: int,
    reorder_point: Decimal,
    target_stock: Decimal,
) -> int:
    """Suggest an integer order quantity, or zero when no reorder is needed."""

    position = require_whole_number(inventory_position, "Inventory Position")
    if not is_reorder_required(position, reorder_point):
        return 0

    shortfall = target_stock - Decimal(position)
    if shortfall <= 0:
        return 0

    return ceil(shortfall)
