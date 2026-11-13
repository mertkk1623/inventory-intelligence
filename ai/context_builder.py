"""Build the minimal, safe AI context from engine results.

Only values the deterministic engine already produced are included. Free-text
workbook content (movement descriptions, product name) is treated as untrusted
data: it is length-capped, stripped of control characters and delivered as a
data payload that the system prompt explicitly forbids interpreting as
instructions.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from analytics.series import (
    ConsumptionSummary,
    consumption_summary,
    daily_consumption_series,
    open_order_rows,
)
from core.models import InventoryCalculation, InventoryDataset

UNTRUSTED_TEXT_LIMIT = 120
MAX_MOVEMENT_ROWS = 40
MAX_OPEN_ORDERS = 20
CONTROL_CHARS = re.compile(r"[\u0000-\u001f\u007f]")

# Phrases that indicate an attempt to override the system instructions. The
# text is not deleted - it is quarantined and flagged so the prompt can warn
# the model that the payload contains adversarial content.
INJECTION_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "disregard previous",
    "forget instructions",
    "system prompt",
    "you are now",
    "act as",
    "new instructions",
    "override",
    "jailbreak",
)


@dataclass(frozen=True)
class AIContext:
    """Everything the model is allowed to see, plus a cache identity."""

    payload: dict
    fingerprint: str
    is_historical: bool
    untrusted_fields: tuple[str, ...]

    def as_json(self) -> str:
        """Serialise the payload for the prompt."""

        return json.dumps(self.payload, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serialisable")


def _sanitise(value: str) -> tuple[str, bool]:
    """Return cleaned text and whether a suspicious phrase was found."""

    text = CONTROL_CHARS.sub(" ", str(value or ""))
    text = " ".join(text.split())
    lowered = text.lower()
    suspicious = any(pattern in lowered for pattern in INJECTION_PATTERNS)
    return text[:UNTRUSTED_TEXT_LIMIT], suspicious


def _decimal(value: Decimal | None, places: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), places)


def _consumption_payload(summary: ConsumptionSummary, unit: str) -> dict:
    quantities = [entry.quantity for entry in summary.days]
    zero_days = sum(1 for quantity in quantities if quantity == 0)
    return {
        "window_days": len(quantities),
        "total_consumption": summary.total,
        "highest_day": summary.highest_day.isoformat() if summary.highest_day else None,
        "highest_quantity": summary.highest_quantity,
        "lowest_day": summary.lowest_day.isoformat() if summary.lowest_day else None,
        "lowest_quantity": summary.lowest_quantity,
        "zero_consumption_days": zero_days,
        "active_days": len(quantities) - zero_days,
        "daily_quantities": quantities,
        "unit": unit,
    }


def build_ai_context(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> AIContext:
    """Assemble the AI context from one engine result.

    The calculation object must belong to ``dataset`` and to its own report
    date; the function refuses mismatched inputs so the model can never be
    shown numbers that the dashboard does not show.
    """

    if not isinstance(dataset, InventoryDataset):
        raise TypeError("A validated InventoryDataset is required for AI context.")
    if not isinstance(calculation, InventoryCalculation):
        raise TypeError("The calculation engine result is required for AI context.")
    if calculation.report_date < dataset.product.opening_stock_date:
        raise ValueError(
            "The report date is before the opening stock date; there is no "
            "context to analyse."
        )

    product = dataset.product
    unit = product.unit
    untrusted: list[str] = []

    product_name, suspicious = _sanitise(product.product_name)
    if suspicious:
        untrusted.append("product_name")

    daily = daily_consumption_series(dataset, calculation.report_date)
    summary = consumption_summary(daily)

    movements = [
        movement
        for movement in dataset.movements
        if movement.date <= calculation.report_date
    ]
    movements.sort(key=lambda movement: movement.date, reverse=True)
    recent = []
    for movement in movements[:MAX_MOVEMENT_ROWS]:
        description, flagged = _sanitise(movement.description)
        if flagged:
            untrusted.append(f"movement:{movement.date.isoformat()}")
        recent.append(
            {
                "date": movement.date.isoformat(),
                "type": movement.transaction_type,
                "quantity": int(movement.quantity),
                "description": description,
            }
        )

    orders = open_order_rows(dataset, calculation.report_date)
    open_orders = [
        {
            "order_no": row.order.order_no,
            "quantity": int(row.order.order_quantity),
            "expected_delivery": row.order.expected_delivery_date.isoformat(),
            "overdue": row.is_overdue,
            "included_in_position": calculation.replenishment_supported,
        }
        for row in orders[:MAX_OPEN_ORDERS]
    ]

    payload = {
        "report_type": "historical" if calculation.is_historical_report else "current",
        "report_date": calculation.report_date.isoformat(),
        "unit": unit,
        "product": {
            "code": product.product_code,
            "name": product_name,
            "opening_stock": int(product.opening_stock),
            "opening_stock_date": product.opening_stock_date.isoformat(),
            "safety_stock": int(product.safety_stock),
            "lead_time_days": int(product.lead_time_days),
            "target_coverage_days": int(product.target_coverage_days),
        },
        "stock": {
            "current_stock": int(calculation.current_stock),
            "total_in": int(calculation.total_in),
            "total_out": int(calculation.total_out),
            "lowest_stock_balance": int(calculation.lowest_stock_balance),
            "negative_stock_warning": calculation.negative_stock_warning,
        },
        "consumption": {
            **_consumption_payload(summary, unit),
            "average_daily": _decimal(calculation.average_daily_consumption),
            "coverage_days": int(calculation.consumption_coverage_days),
            "days_of_supply": _decimal(calculation.days_of_supply, 2),
        },
        "replenishment": {
            "supported": calculation.replenishment_supported,
            "reorder_point": _decimal(calculation.reorder_point, 2),
            "target_stock": _decimal(calculation.target_stock, 2),
            "inventory_position": int(calculation.inventory_position),
            "open_order_quantity": int(calculation.total_open_order_quantity),
            "overdue_order_count": int(calculation.overdue_order_count),
            "suggested_order_quantity": int(calculation.suggested_order_quantity),
            "reorder_required": calculation.reorder_required,
            "note": calculation.replenishment_note,
        },
        "counts": {
            "movements_in_range": len(movements),
            "open_orders": len(orders),
        },
        "recent_movements": recent,
        "open_orders": open_orders,
    }

    fingerprint = context_fingerprint(dataset, calculation)
    return AIContext(
        payload=payload,
        fingerprint=fingerprint,
        is_historical=calculation.is_historical_report,
        untrusted_fields=tuple(sorted(set(untrusted))),
    )


def context_fingerprint(
    dataset: InventoryDataset,
    calculation: InventoryCalculation,
) -> str:
    """Return a stable identity for cache invalidation.

    The fingerprint covers the dataset identity, the report date and every
    calculation value the AI interprets. If any of them changes, the key
    changes and the cached answer is discarded.
    """

    identity = {
        "source": dataset.source,
        "filename": dataset.filename,
        "product_code": dataset.product.product_code,
        "movement_count": dataset.movement_count,
        "open_order_count": dataset.open_order_count,
        "report_date": calculation.report_date.isoformat(),
        "current_stock": calculation.current_stock,
        "total_in": calculation.total_in,
        "total_out": calculation.total_out,
        "average_daily_consumption": str(calculation.average_daily_consumption),
        "days_of_supply": (
            str(calculation.days_of_supply)
            if calculation.days_of_supply is not None
            else None
        ),
        "reorder_point": str(calculation.reorder_point),
        "target_stock": str(calculation.target_stock),
        "inventory_position": calculation.inventory_position,
        "open_order_quantity": calculation.total_open_order_quantity,
        "overdue_order_count": calculation.overdue_order_count,
        "suggested_order_quantity": calculation.suggested_order_quantity,
        "reorder_required": calculation.reorder_required,
        "replenishment_supported": calculation.replenishment_supported,
        "is_historical_report": calculation.is_historical_report,
    }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
