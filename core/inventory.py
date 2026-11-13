"""Current stock and movement processing for the single-SKU workspace.

The functions in this module are independent from Streamlit. They only
consume validated domain models and return immutable value objects.
"""

from __future__ import annotations

import numbers
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from core.models import ProductMaster, StockMovement

TRANSACTION_IN = "IN"
TRANSACTION_OUT = "OUT"
VALID_TRANSACTION_TYPES = (TRANSACTION_IN, TRANSACTION_OUT)


@dataclass(frozen=True)
class StockPosition:
    """Stock balance after applying movements up to a report date."""

    current_stock: int
    total_in: int
    total_out: int
    lowest_stock_balance: int
    negative_stock_warning: bool


def as_date(value: date | datetime, field_name: str) -> date:
    """Normalise a date-like value, raising a clear error otherwise."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"{field_name} must be a valid date.")


def require_whole_number(
    value,
    label: str,
    *,
    minimum: int | None = None,
) -> int:
    """Return ``value`` as an ``int`` or raise a clear contract error."""

    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{label} must be a whole number.")

    number = int(value)
    if minimum is not None and number < minimum:
        raise ValueError(f"{label} must be {minimum} or greater.")
    return number


def validate_movements(
    movements: Iterable[StockMovement],
    opening_stock_date: date,
) -> None:
    """Validate the movement contract expected by the calculation engine.

    The Excel validator already enforces these rules. Keeping a defensive
    check here means a directly constructed dataset can never produce a
    silently wrong balance.
    """

    opening_date = as_date(opening_stock_date, "opening stock date")

    for movement in movements:
        movement_date = as_date(movement.date, "movement date")

        if movement_date < opening_date:
            raise ValueError(
                f"Movement dated {movement_date.isoformat()} is before the "
                f"opening stock date {opening_date.isoformat()}."
            )

        if movement.transaction_type not in VALID_TRANSACTION_TYPES:
            raise ValueError(
                "Movement Transaction Type must be IN or OUT. "
                f"Received '{movement.transaction_type}'."
            )

        require_whole_number(
            movement.quantity, "Movement quantity", minimum=1
        )


def calculate_stock_position(
    product: ProductMaster,
    movements: Iterable[StockMovement],
    report_date: date,
) -> StockPosition:
    """Calculate current stock using movements on or before ``report_date``.

    Movements are processed in date order. For movements on the same date the
    original dataset order is preserved. The opening balance is never
    clamped, so a negative balance remains visible to callers.
    """

    report = as_date(report_date, "report date")
    opening_date = as_date(product.opening_stock_date, "opening stock date")

    opening_stock = require_whole_number(
        product.opening_stock, "Opening Stock", minimum=0
    )

    ordered_movements = sorted(
        movements,
        key=lambda movement: as_date(movement.date, "movement date"),
    )
    validate_movements(ordered_movements, opening_date)

    balance = opening_stock
    lowest_balance = balance
    total_in = 0
    total_out = 0

    for movement in ordered_movements:
        movement_date = as_date(movement.date, "movement date")
        if movement_date > report:
            continue

        quantity = int(movement.quantity)
        if movement.transaction_type == TRANSACTION_IN:
            balance += quantity
            total_in += quantity
        else:
            balance -= quantity
            total_out += quantity

        lowest_balance = min(lowest_balance, balance)

    return StockPosition(
        current_stock=balance,
        total_in=total_in,
        total_out=total_out,
        lowest_stock_balance=lowest_balance,
        negative_stock_warning=lowest_balance < 0,
    )


def stock_balance_history(
    product: ProductMaster,
    movements: Iterable[StockMovement],
    report_date: date,
) -> tuple[tuple[date, int], ...]:
    """Return the daily closing balance from the opening date to ``report_date``.

    This is the only place where the chart-facing balance path is produced, so
    the UI never repeats a stock formula. The path includes every calendar day;
    days without a movement repeat the previous closing balance.
    """

    report = as_date(report_date, "report date")
    opening_date = as_date(product.opening_stock_date, "opening stock date")

    if report < opening_date:
        raise ValueError(
            f"Report date {report.isoformat()} is before the opening stock date "
            f"{opening_date.isoformat()}."
        )

    opening_stock = require_whole_number(
        product.opening_stock, "Opening Stock", minimum=0
    )

    ordered_movements = sorted(
        movements,
        key=lambda movement: as_date(movement.date, "movement date"),
    )
    validate_movements(ordered_movements, opening_date)

    net_by_day: dict[date, int] = {}
    for movement in ordered_movements:
        movement_date = as_date(movement.date, "movement date")
        if movement_date > report:
            continue

        quantity = int(movement.quantity)
        delta = (
            quantity
            if movement.transaction_type == TRANSACTION_IN
            else -quantity
        )
        net_by_day[movement_date] = net_by_day.get(movement_date, 0) + delta

    history: list[tuple[date, int]] = []
    balance = opening_stock
    day = opening_date
    while day <= report:
        balance += net_by_day.get(day, 0)
        history.append((day, balance))
        day += timedelta(days=1)

    return tuple(history)
