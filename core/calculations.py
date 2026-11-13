"""UI-independent inventory calculation engine.

This module composes the inventory, consumption and replenishment building
blocks into one structured result. It deliberately contains no Streamlit
imports and no formatting logic.
"""

from __future__ import annotations

from datetime import date

from core.consumption import (
    CONSUMPTION_WINDOW_DAYS,
    calculate_consumption,
    calculate_days_of_supply,
)
from core.inventory import (
    as_date,
    calculate_stock_position,
    require_whole_number,
)
from core.models import (
    InventoryCalculation,
    InventoryDataset,
    ProductMaster,
)
from core.replenishment import (
    calculate_inventory_position,
    calculate_reorder_point,
    calculate_suggested_order_quantity,
    calculate_target_stock,
    count_overdue_orders,
    is_reorder_required,
)

HISTORICAL_REPLENISHMENT_NOTE = (
    "Historical reports do not include current open orders and do not produce "
    "order suggestions. Replenishment planning is supported only for the "
    "current report date."
)


def calculate_inventory(
    dataset: InventoryDataset,
    report_date: date,
    *,
    today: date | None = None,
    consumption_window_days: int = CONSUMPTION_WINDOW_DAYS,
) -> InventoryCalculation:
    """Calculate inventory metrics for one validated single-SKU dataset.

    Parameters
    ----------
    dataset:
        A validated :class:`~core.models.InventoryDataset`.
    report_date:
        The inclusive cut-off date for stock movements and consumption.
    today:
        Optional reference date used to detect historical reports. Defaults to
        ``date.today()``. Tests pass a fixed value to stay deterministic.
    consumption_window_days:
        Rolling calendar window for average daily consumption. Defaults to 30.

    Historical reports intentionally exclude current open orders, set
    ``reorder_required`` to ``False`` and do not produce an order suggestion.
    Descriptive historical metrics such as current stock, consumption,
    reorder point and target stock are still calculated.
    """

    product = dataset.product
    report = as_date(report_date, "report date")
    current_day = as_date(today, "today") if today is not None else date.today()

    opening_date = _validate_product(product)
    if report < opening_date:
        raise ValueError(
            f"Report date {report.isoformat()} is before the opening stock date "
            f"{opening_date.isoformat()}."
        )

    _validate_open_orders(dataset)

    stock = calculate_stock_position(product, dataset.movements, report)
    consumption = calculate_consumption(
        dataset.movements,
        opening_date,
        report,
        window_days=consumption_window_days,
    )
    days_of_supply = calculate_days_of_supply(
        stock.current_stock, consumption.average_daily_consumption
    )
    reorder_point = calculate_reorder_point(
        consumption.average_daily_consumption,
        product.lead_time_days,
        product.safety_stock,
    )
    target_stock = calculate_target_stock(
        consumption.average_daily_consumption,
        product.lead_time_days,
        product.target_coverage_days,
        product.safety_stock,
    )

    is_historical = report < current_day

    if is_historical:
        # Current open orders describe today's supply, not the supply that
        # existed on a past report date. Historical order planning is out of
        # scope for V1, so no order suggestion is produced.
        total_open_order_quantity = 0
        inventory_position = stock.current_stock
        overdue_order_count = 0
        reorder_required = False
        suggested_order_quantity = 0
        replenishment_note = HISTORICAL_REPLENISHMENT_NOTE
    else:
        total_open_order_quantity = sum(
            int(order.order_quantity) for order in dataset.open_orders
        )
        inventory_position = calculate_inventory_position(
            stock.current_stock, dataset.open_orders
        )
        overdue_order_count = count_overdue_orders(
            dataset.open_orders, report
        )
        reorder_required = is_reorder_required(
            inventory_position, reorder_point
        )
        suggested_order_quantity = calculate_suggested_order_quantity(
            inventory_position, reorder_point, target_stock
        )
        replenishment_note = ""

    return InventoryCalculation(
        report_date=report,
        current_stock=stock.current_stock,
        total_in=stock.total_in,
        total_out=stock.total_out,
        average_daily_consumption=consumption.average_daily_consumption,
        consumption_coverage_days=consumption.coverage_days,
        days_of_supply=days_of_supply,
        safety_stock=int(product.safety_stock),
        lead_time_days=int(product.lead_time_days),
        reorder_point=reorder_point,
        total_open_order_quantity=total_open_order_quantity,
        inventory_position=inventory_position,
        target_stock=target_stock,
        suggested_order_quantity=suggested_order_quantity,
        overdue_order_count=overdue_order_count,
        negative_stock_warning=stock.negative_stock_warning,
        reorder_required=reorder_required,
        lowest_stock_balance=stock.lowest_stock_balance,
        is_historical_report=is_historical,
        replenishment_supported=not is_historical,
        replenishment_note=replenishment_note,
    )


def _validate_product(product: ProductMaster) -> date:
    """Validate product-level engine inputs and return the opening date."""

    opening_date = as_date(product.opening_stock_date, "opening stock date")
    require_whole_number(product.opening_stock, "Opening Stock", minimum=0)
    require_whole_number(product.safety_stock, "Safety Stock", minimum=0)
    require_whole_number(product.lead_time_days, "Lead Time Days", minimum=0)
    require_whole_number(
        product.target_coverage_days, "Target Coverage Days", minimum=1
    )
    return opening_date


def _validate_open_orders(dataset: InventoryDataset) -> None:
    for order in dataset.open_orders:
        require_whole_number(order.order_quantity, "Order Quantity", minimum=1)
        as_date(order.expected_delivery_date, "expected delivery date")
