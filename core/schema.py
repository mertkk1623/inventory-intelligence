"""Canonical Excel workbook schema.

The column names in this module must stay in sync with the files in
``templates/``. They are the contract between the workbook and the app.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SheetSpec:
    """Description of one required worksheet."""

    name: str
    description: str
    required_columns: tuple[str, ...]


PRODUCT_MASTER_SPEC = SheetSpec(
    name="Product Master",
    description=(
        "One row describing your single SKU, its opening stock and the "
        "planning parameters used by later modules."
    ),
    required_columns=(
        "Product Code",
        "Product Name",
        "Unit",
        "Opening Stock",
        "Opening Stock Date",
        "Safety Stock",
        "Lead Time Days",
        "Target Coverage Days",
    ),
)

STOCK_MOVEMENTS_SPEC = SheetSpec(
    name="Stock Movements",
    description=(
        "Dated IN and OUT transactions recorded on or after the opening "
        "stock date. Each row represents one movement."
    ),
    required_columns=(
        "Date",
        "Transaction Type",
        "Quantity",
        "Description",
    ),
)

OPEN_ORDERS_SPEC = SheetSpec(
    name="Open Orders",
    description=(
        "Purchase orders that have been placed but not yet delivered. "
        "Order numbers must be unique."
    ),
    required_columns=(
        "Order No",
        "Order Quantity",
        "Expected Delivery Date",
    ),
)

SHEET_SPECS: tuple[SheetSpec, ...] = (
    PRODUCT_MASTER_SPEC,
    STOCK_MOVEMENTS_SPEC,
    OPEN_ORDERS_SPEC,
)

REQUIRED_SHEETS: tuple[str, ...] = tuple(spec.name for spec in SHEET_SPECS)

TRANSACTION_TYPES: tuple[str, ...] = ("IN", "OUT")

SUPPORTED_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
)
