"""Consumption metrics for the single-SKU workspace.

Average daily consumption uses a rolling calendar window. Days without any
OUT movement still count toward the covered days, which keeps the average
from being inflated by only looking at active days.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from core.inventory import (
    TRANSACTION_OUT,
    as_date,
    require_whole_number,
    validate_movements,
)
from core.models import StockMovement

CONSUMPTION_WINDOW_DAYS = 30


@dataclass(frozen=True)
class ConsumptionMetrics:
    """OUT consumption within the rolling consumption window."""

    total_out: int
    coverage_days: int
    average_daily_consumption: Decimal
    window_start: date
    window_end: date


def consumption_window(
    opening_stock_date: date,
    report_date: date,
    *,
    window_days: int = CONSUMPTION_WINDOW_DAYS,
) -> tuple[date, date]:
    """Return the inclusive consumption window for a report date.

    The window never starts before the opening stock date. If the report date
    is earlier than the opening date, the returned start is later than the
    end and the caller treats coverage as zero.
    """

    if isinstance(window_days, bool) or not isinstance(window_days, int):
        raise ValueError("Consumption window must be a whole number of days.")
    if window_days < 1:
        raise ValueError("Consumption window must be at least one day.")

    opening_date = as_date(opening_stock_date, "opening stock date")
    report = as_date(report_date, "report date")
    earliest = report - timedelta(days=window_days - 1)

    return max(opening_date, earliest), report


def calculate_consumption(
    movements: Iterable[StockMovement],
    opening_stock_date: date,
    report_date: date,
    *,
    window_days: int = CONSUMPTION_WINDOW_DAYS,
) -> ConsumptionMetrics:
    """Calculate average daily consumption for the report date.

    Zero consumption returns ``Decimal("0")`` rather than raising a division
    error. Coverage is zero when the report date predates the opening date.
    """

    opening_date = as_date(opening_stock_date, "opening stock date")
    report = as_date(report_date, "report date")

    movement_list = tuple(movements)
    validate_movements(movement_list, opening_date)

    window_start, window_end = consumption_window(
        opening_date, report, window_days=window_days
    )

    if window_end < window_start:
        coverage_days = 0
        total_out = 0
    else:
        coverage_days = (window_end - window_start).days + 1
        total_out = sum(
            int(movement.quantity)
            for movement in movement_list
            if movement.transaction_type == TRANSACTION_OUT
            and window_start
            <= as_date(movement.date, "movement date")
            <= window_end
        )

    average = (
        Decimal(total_out) / Decimal(coverage_days)
        if coverage_days > 0
        else Decimal(0)
    )

    return ConsumptionMetrics(
        total_out=total_out,
        coverage_days=coverage_days,
        average_daily_consumption=average,
        window_start=window_start,
        window_end=window_end,
    )


def calculate_days_of_supply(
    current_stock: int,
    average_daily_consumption: Decimal,
) -> Decimal | None:
    """Return stock coverage in days, or ``None`` when consumption is zero."""

    if average_daily_consumption == 0:
        return None

    stock = require_whole_number(current_stock, "Current Stock")
    return Decimal(stock) / average_daily_consumption
