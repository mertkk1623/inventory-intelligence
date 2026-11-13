"""UI-independent time series and table derivations.

The calculation engine remains the single source of truth for stock balances
and planning values. This module only reshapes validated movements into
chart-ready series, always filling missing calendar days with zero or with
the last known balance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from core.consumption import CONSUMPTION_WINDOW_DAYS, consumption_window
from core.inventory import (
    TRANSACTION_IN,
    TRANSACTION_OUT,
    as_date,
    stock_balance_history,
)
from core.models import (
    InventoryCalculation,
    InventoryDataset,
    OpenOrder,
    StockMovement,
)


@dataclass(frozen=True)
class DailyConsumption:
    day: date
    quantity: int


@dataclass(frozen=True)
class WeeklyConsumption:
    week_start: date
    quantity: int


@dataclass(frozen=True)
class ConsumptionSummary:
    total: int
    days: tuple[DailyConsumption, ...]
    highest_day: date | None
    highest_quantity: int
    lowest_day: date | None
    lowest_quantity: int


@dataclass(frozen=True)
class OpenOrderRow:
    order: OpenOrder
    is_overdue: bool


def stock_balance_series(
    dataset: InventoryDataset,
    report_date: date,
) -> tuple[tuple[date, int], ...]:
    """Return a zero-gap daily stock balance series through ``report_date``.

    Balances come from the Package 2 stock engine, so the UI never repeats a
    stock formula of its own.
    """

    return stock_balance_history(dataset.product, dataset.movements, report_date)


def daily_consumption_series(
    dataset: InventoryDataset,
    report_date: date,
    *,
    window_days: int = CONSUMPTION_WINDOW_DAYS,
) -> tuple[DailyConsumption, ...]:
    """Return OUT consumption for every calendar day in the window.

    Days without an OUT movement are included with quantity ``0`` so the
    charts never compress zero-consumption days out of the timeline.
    """

    product = dataset.product
    report = as_date(report_date, "report date")
    start, end = consumption_window(
        product.opening_stock_date,
        report,
        window_days=window_days,
    )
    if end < start:
        return ()

    out_by_day: dict[date, int] = {}
    for movement in dataset.movements:
        movement_date = as_date(movement.date, "movement date")
        if (
            movement.transaction_type == TRANSACTION_OUT
            and start <= movement_date <= end
        ):
            out_by_day[movement_date] = (
                out_by_day.get(movement_date, 0) + int(movement.quantity)
            )

    days: list[DailyConsumption] = []
    day = start
    while day <= end:
        days.append(DailyConsumption(day=day, quantity=out_by_day.get(day, 0)))
        day += timedelta(days=1)
    return tuple(days)


def weekly_consumption_series(
    daily: tuple[DailyConsumption, ...] | list[DailyConsumption],
) -> tuple[WeeklyConsumption, ...]:
    """Aggregate daily consumption into Monday-based weeks with no gaps."""

    if not daily:
        return ()

    by_week: dict[date, int] = {}
    for entry in daily:
        week_start = entry.day - timedelta(days=entry.day.weekday())
        by_week[week_start] = by_week.get(week_start, 0) + entry.quantity

    first_week = min(by_week)
    last_week = max(by_week)
    weeks: list[WeeklyConsumption] = []
    week = first_week
    while week <= last_week:
        weeks.append(
            WeeklyConsumption(week_start=week, quantity=by_week.get(week, 0))
        )
        week += timedelta(days=7)
    return tuple(weeks)


def consumption_summary(
    daily: tuple[DailyConsumption, ...] | list[DailyConsumption],
) -> ConsumptionSummary:
    """Summarise a daily consumption series, including zero days."""

    if not daily:
        return ConsumptionSummary(
            total=0,
            days=(),
            highest_day=None,
            highest_quantity=0,
            lowest_day=None,
            lowest_quantity=0,
        )

    entries = tuple(daily)
    highest = max(entries, key=lambda entry: entry.quantity)
    lowest = min(entries, key=lambda entry: entry.quantity)
    return ConsumptionSummary(
        total=sum(entry.quantity for entry in entries),
        days=entries,
        highest_day=highest.day,
        highest_quantity=highest.quantity,
        lowest_day=lowest.day,
        lowest_quantity=lowest.quantity,
    )


def filter_movements(
    dataset: InventoryDataset,
    start: date,
    end: date,
    transaction_types: tuple[str, ...] | list[str] | None = None,
) -> tuple[StockMovement, ...]:
    """Filter movement history for the Stock Analysis screen.

    Results are newest first. For movements on the same date the original
    workbook order is preserved.
    """

    start_date = as_date(start, "start date")
    end_date = as_date(end, "end date")
    allowed = (
        (TRANSACTION_IN, TRANSACTION_OUT)
        if not transaction_types
        else tuple(transaction_types)
    )

    selected = [
        movement
        for movement in dataset.movements
        if start_date <= as_date(movement.date, "movement date") <= end_date
        and movement.transaction_type in allowed
    ]
    return tuple(sorted(selected, key=lambda movement: movement.date, reverse=True))


def movement_totals(
    movements: tuple[StockMovement, ...] | list[StockMovement],
) -> tuple[int, int]:
    """Return ``(total_in, total_out)`` for a movement selection."""

    total_in = sum(
        int(movement.quantity)
        for movement in movements
        if movement.transaction_type == TRANSACTION_IN
    )
    total_out = sum(
        int(movement.quantity)
        for movement in movements
        if movement.transaction_type == TRANSACTION_OUT
    )
    return total_in, total_out


def open_order_rows(
    dataset: InventoryDataset,
    report_date: date,
) -> tuple[OpenOrderRow, ...]:
    """Return open orders with an overdue flag for the report date."""

    report = as_date(report_date, "report date")
    rows = [
        OpenOrderRow(
            order=order,
            is_overdue=as_date(
                order.expected_delivery_date, "expected delivery date"
            )
            < report,
        )
        for order in dataset.open_orders
    ]
    return tuple(
        sorted(rows, key=lambda row: row.order.expected_delivery_date)
    )


def stock_status_label(calculation: InventoryCalculation) -> str:
    """Classify the current stock position for display only."""

    if calculation.negative_stock_warning:
        return "Negative stock"
    if calculation.reorder_required:
        return "Reorder required"
    if calculation.current_stock <= calculation.safety_stock:
        return "Below safety stock"
    return "Healthy"
