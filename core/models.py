"""Immutable domain models for a validated inventory workbook."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# Dataset provenance. ``config`` re-exports these so the UI has one source of
# truth; the domain layer owns them because they describe domain data.
DEMO_SOURCE = "demo"
SAMPLE_SOURCE = "sample"
UPLOAD_SOURCE = "upload"

# Both the bundled workbook and the generated Quick Start scenarios are
# synthetic and must be labelled as demo data in the interface.
DEMO_SOURCES = (DEMO_SOURCE, SAMPLE_SOURCE)


@dataclass(frozen=True)
class ProductMaster:
    """The single SKU supported by V1."""

    product_code: str
    product_name: str
    unit: str
    opening_stock: int
    opening_stock_date: date
    safety_stock: int
    lead_time_days: int
    target_coverage_days: int


@dataclass(frozen=True)
class StockMovement:
    """A single IN or OUT stock transaction."""

    date: date
    transaction_type: str
    quantity: int
    description: str = ""


@dataclass(frozen=True)
class OpenOrder:
    """A purchase order that has not yet been delivered."""

    order_no: str
    order_quantity: int
    expected_delivery_date: date


@dataclass(frozen=True)
class InventoryDataset:
    """A fully validated, in-memory dataset for one product."""

    product: ProductMaster
    movements: tuple[StockMovement, ...]
    open_orders: tuple[OpenOrder, ...]
    source: str
    filename: str

    @property
    def is_demo(self) -> bool:
        """True for any synthetic dataset shipped with the product.

        Both the bundled demo workbook and the generated sample scenarios are
        synthetic, so the UI labels them as demo data rather than as an
        uploaded customer file.
        """

        return self.source in DEMO_SOURCES

    @property
    def is_sample(self) -> bool:
        """True only for a generated Quick Start sample scenario."""

        return self.source == SAMPLE_SOURCE

    @property
    def movement_count(self) -> int:
        return len(self.movements)

    @property
    def open_order_count(self) -> int:
        return len(self.open_orders)


@dataclass(frozen=True)
class InventoryCalculation:
    """Structured result of the single-SKU inventory calculation engine.

    Whole-unit quantities are integers. Rates and planning values use
    :class:`~decimal.Decimal` so the engine does not depend on binary
    floating-point rounding. ``days_of_supply`` is ``None`` when average
    daily consumption is zero.

    ``lowest_stock_balance`` records the lowest running balance seen while
    processing movements up to the report date, which makes a negative
    stock warning explainable even when the final balance has recovered.
    """

    report_date: date
    current_stock: int
    total_in: int
    total_out: int
    average_daily_consumption: Decimal
    consumption_coverage_days: int
    days_of_supply: Decimal | None
    safety_stock: int
    lead_time_days: int
    reorder_point: Decimal
    total_open_order_quantity: int
    inventory_position: int
    target_stock: Decimal
    suggested_order_quantity: int
    overdue_order_count: int
    negative_stock_warning: bool
    reorder_required: bool
    lowest_stock_balance: int
    is_historical_report: bool
    replenishment_supported: bool
    replenishment_note: str
