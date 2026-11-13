"""Excel validation engine.

The validator is deliberately independent from Streamlit. It accepts a file
path, bytes or a binary stream and returns a :class:`ValidationResult` that
contains human-readable issues plus a domain dataset when the workbook is
valid.

Validation never raises for bad user data. Unreadable files and malformed
rows are reported as issues instead.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from core.excel_reader import ExcelReadError, read_workbook
from core.models import InventoryDataset, OpenOrder, ProductMaster, StockMovement
from core.schema import (
    OPEN_ORDERS_SPEC,
    PRODUCT_MASTER_SPEC,
    STOCK_MOVEMENTS_SPEC,
    SUPPORTED_DATE_FORMATS,
    TRANSACTION_TYPES,
    SheetSpec,
)
from utils.i18n import LocalisedMessage

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """A single problem found in a workbook."""

    severity: str
    code: str
    message: str
    sheet: str | None = None
    row: int | None = None
    column: str | None = None

    @property
    def location(self) -> str:
        parts: list[str] = []
        if self.sheet:
            parts.append(self.sheet)
        if self.row:
            parts.append(f"row {self.row}")
        if self.column:
            parts.append(self.column)
        return " · ".join(parts)


@dataclass
class ValidationResult:
    """Outcome of validating one workbook."""

    filename: str
    source: str
    issues: list[ValidationIssue] = field(default_factory=list)
    dataset: InventoryDataset | None = None
    sheets_found: tuple[str, ...] = ()

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == WARNING]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def is_valid(self) -> bool:
        return self.dataset is not None and not self.errors

    def issues_for_sheet(self, sheet: str) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.sheet == sheet]


def validate_excel(
    source: str | Path | BinaryIO | bytes,
    *,
    filename: str | None = None,
    source_kind: str = "upload",
) -> ValidationResult:
    """Validate a workbook and build a dataset when every rule passes."""

    workbook_name = filename or getattr(source, "name", None) or "workbook.xlsx"
    result = ValidationResult(filename=workbook_name, source=source_kind)

    try:
        sheets = read_workbook(source, filename=workbook_name)
    except ExcelReadError as exc:
        result.issues.append(
            ValidationIssue(
                severity=ERROR,
                code="file_unreadable",
                message=str(exc),
            )
        )
        return result

    result.sheets_found = tuple(sheets.keys())

    if not sheets:
        result.issues.append(
            ValidationIssue(
                severity=ERROR,
                code="empty_workbook",
                message=LocalisedMessage("The workbook does not contain any worksheets."),
            )
        )
        return result

    missing_sheets = [spec.name for spec in _sheet_specs() if spec.name not in sheets]
    for sheet_name in missing_sheets:
        result.issues.append(
            ValidationIssue(
                severity=ERROR,
                code="missing_sheet",
                message=LocalisedMessage("Required worksheet '{sheet}' is missing.", sheet=sheet_name),
                sheet=sheet_name,
            )
        )

    product: ProductMaster | None = None
    opening_date: date | None = None
    movements: tuple[StockMovement, ...] = ()
    open_orders: tuple[OpenOrder, ...] = ()

    if PRODUCT_MASTER_SPEC.name in sheets:
        product, opening_date = _validate_product_master(
            sheets[PRODUCT_MASTER_SPEC.name], result
        )

    if STOCK_MOVEMENTS_SPEC.name in sheets:
        movements = _validate_stock_movements(
            sheets[STOCK_MOVEMENTS_SPEC.name], opening_date, result
        )

    if OPEN_ORDERS_SPEC.name in sheets:
        open_orders = _validate_open_orders(
            sheets[OPEN_ORDERS_SPEC.name], result
        )

    if product is not None and not result.errors and not missing_sheets:
        result.dataset = InventoryDataset(
            product=product,
            movements=movements,
            open_orders=open_orders,
            source=source_kind,
            filename=workbook_name,
        )

    return result


def validate_excel_file(
    path: str | Path,
    *,
    source_kind: str = "upload",
) -> ValidationResult:
    """Convenience wrapper for validating a workbook on disk."""

    workbook_path = Path(path)
    return validate_excel(
        workbook_path,
        filename=workbook_path.name,
        source_kind=source_kind,
    )


def _sheet_specs() -> tuple[SheetSpec, ...]:
    return (PRODUCT_MASTER_SPEC, STOCK_MOVEMENTS_SPEC, OPEN_ORDERS_SPEC)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return False


def _text(value: Any) -> str:
    return "" if _is_blank(value) else str(value).strip()


def _parse_integer(value: Any) -> int | None:
    """Return an integer for whole numeric values, otherwise ``None``."""

    if _is_blank(value) or isinstance(value, bool):
        return None

    if isinstance(value, numbers.Integral):
        return int(value)

    if isinstance(value, numbers.Real):
        numeric = float(value)
        if math.isfinite(numeric) and numeric.is_integer():
            return int(numeric)
        return None

    if isinstance(value, str):
        try:
            numeric = float(value.strip())
        except ValueError:
            return None
        if math.isfinite(numeric) and numeric.is_integer():
            return int(numeric)
        return None

    return None


def _parse_date(value: Any) -> date | None:
    """Parse Excel dates, Python dates and common text date formats."""

    if _is_blank(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        # Support raw Excel serial dates (for example 46300).
        try:
            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        except (OverflowError, ValueError):
            return None

    if isinstance(value, str):
        candidate = value.strip()
        for date_format in SUPPORTED_DATE_FORMATS:
            try:
                return datetime.strptime(candidate, date_format).date()
            except ValueError:
                continue

    return None


def _data_rows(frame: pd.DataFrame) -> Iterator[tuple[int, pd.Series]]:
    """Yield non-empty rows with their zero-based DataFrame index."""

    for index, row in frame.iterrows():
        if all(_is_blank(value) for value in row.tolist()):
            continue
        yield int(index), row


def _check_columns(
    frame: pd.DataFrame,
    spec: SheetSpec,
    result: ValidationResult,
) -> bool:
    missing = [column for column in spec.required_columns if column not in frame.columns]
    if missing:
        result.issues.append(
            ValidationIssue(
                severity=ERROR,
                code="missing_columns",
                message=LocalisedMessage(
                    "Missing required column(s): {columns}. Keep the template "
                    "column names unchanged.",
                    columns=", ".join(missing),
                ),
                sheet=spec.name,
            )
        )

    unexpected = [column for column in frame.columns if column not in spec.required_columns]
    if unexpected:
        result.issues.append(
            ValidationIssue(
                severity=WARNING,
                code="unexpected_columns",
                message=LocalisedMessage(
                    "Extra column(s) will be ignored: {columns}",
                    columns=", ".join(map(str, unexpected)),
                ),
                sheet=spec.name,
            )
        )

    return not missing


def _validate_product_master(
    frame: pd.DataFrame,
    result: ValidationResult,
) -> tuple[ProductMaster | None, date | None]:
    if not _check_columns(frame, PRODUCT_MASTER_SPEC, result):
        return None, None

    rows = list(_data_rows(frame))
    if not rows:
        result.issues.append(
            ValidationIssue(
                severity=ERROR,
                code="empty_product_master",
                message=LocalisedMessage(
                    "Product Master must contain exactly one product row. "
                    "No product data was found."
                ),
                sheet=PRODUCT_MASTER_SPEC.name,
            )
        )
        return None, None

    if len(rows) > 1:
        excel_rows = ", ".join(str(index + 2) for index, _ in rows)
        result.issues.append(
            ValidationIssue(
                severity=ERROR,
                code="multiple_products",
                message=LocalisedMessage(
                    "V1 supports a single product, but {count} product rows "
                    "were found (Excel rows: {rows}). Keep exactly one row.",
                    count=len(rows),
                    rows=excel_rows,
                ),
                sheet=PRODUCT_MASTER_SPEC.name,
            )
        )

    product: ProductMaster | None = None
    opening_date: date | None = None
    product_codes: list[tuple[int, str]] = []

    for index, row in rows:
        excel_row = index + 2
        values: dict[str, Any] = {}
        row_is_valid = True

        product_code = _text(row.get("Product Code"))
        if not product_code:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="required_field",
                    message=LocalisedMessage("Product Code is required."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Product Code",
                )
            )
            row_is_valid = False
        else:
            product_codes.append((excel_row, product_code))
        values["product_code"] = product_code

        product_name = _text(row.get("Product Name"))
        if not product_name:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="required_field",
                    message=LocalisedMessage("Product Name is required."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Product Name",
                )
            )
            row_is_valid = False
        values["product_name"] = product_name

        unit = _text(row.get("Unit"))
        if not unit:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="required_field",
                    message=LocalisedMessage("Unit is required (for example: pcs, kg, m)."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Unit",
                )
            )
            row_is_valid = False
        values["unit"] = unit

        opening_stock = _parse_integer(row.get("Opening Stock"))
        if opening_stock is None or opening_stock < 0:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_quantity",
                    message=LocalisedMessage("Opening Stock must be a whole number of 0 or greater."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Opening Stock",
                )
            )
            row_is_valid = False
        values["opening_stock"] = opening_stock

        parsed_opening_date = _parse_date(row.get("Opening Stock Date"))
        if parsed_opening_date is None:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_date",
                    message=LocalisedMessage(
                        "Opening Stock Date is missing or invalid. Use a valid "
                        "Excel date (for example 2026-10-01)."
                    ),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Opening Stock Date",
                )
            )
            row_is_valid = False
        else:
            opening_date = parsed_opening_date
        values["opening_stock_date"] = parsed_opening_date

        safety_stock = _parse_integer(row.get("Safety Stock"))
        if safety_stock is None or safety_stock < 0:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_quantity",
                    message=LocalisedMessage("Safety Stock must be a whole number of 0 or greater."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Safety Stock",
                )
            )
            row_is_valid = False
        values["safety_stock"] = safety_stock

        lead_time_days = _parse_integer(row.get("Lead Time Days"))
        if lead_time_days is None or lead_time_days < 0:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_integer",
                    message=LocalisedMessage("Lead Time Days must be a whole number of 0 or greater."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Lead Time Days",
                )
            )
            row_is_valid = False
        values["lead_time_days"] = lead_time_days

        target_coverage_days = _parse_integer(row.get("Target Coverage Days"))
        if target_coverage_days is None or target_coverage_days < 1:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_integer",
                    message=LocalisedMessage("Target Coverage Days must be a whole number greater than 0."),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    row=excel_row,
                    column="Target Coverage Days",
                )
            )
            row_is_valid = False
        values["target_coverage_days"] = target_coverage_days

        if row_is_valid and len(rows) == 1:
            product = ProductMaster(
                product_code=values["product_code"],
                product_name=values["product_name"],
                unit=values["unit"],
                opening_stock=values["opening_stock"],
                opening_stock_date=values["opening_stock_date"],
                safety_stock=values["safety_stock"],
                lead_time_days=values["lead_time_days"],
                target_coverage_days=values["target_coverage_days"],
            )

    _check_duplicate_product_codes(product_codes, result)
    return product, opening_date


def _check_duplicate_product_codes(
    product_codes: list[tuple[int, str]],
    result: ValidationResult,
) -> None:
    seen: dict[str, list[int]] = {}
    for excel_row, code in product_codes:
        seen.setdefault(code.casefold(), []).append(excel_row)

    for rows in seen.values():
        if len(rows) > 1:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="duplicate_product_code",
                    message=LocalisedMessage(
                        "Product Code must be unique. Duplicate value found in "
                        "Excel rows: {rows}.",
                        rows=", ".join(map(str, rows)),
                    ),
                    sheet=PRODUCT_MASTER_SPEC.name,
                    column="Product Code",
                )
            )


def _validate_stock_movements(
    frame: pd.DataFrame,
    opening_date: date | None,
    result: ValidationResult,
) -> tuple[StockMovement, ...]:
    if not _check_columns(frame, STOCK_MOVEMENTS_SPEC, result):
        return ()

    rows = list(_data_rows(frame))
    if not rows:
        result.issues.append(
            ValidationIssue(
                severity=WARNING,
                code="no_movements",
                message=LocalisedMessage(
                    "No stock movements were found. The workbook is valid, but "
                    "analysis will be limited without movement history."
                ),
                sheet=STOCK_MOVEMENTS_SPEC.name,
            )
        )
        return ()

    movements: list[StockMovement] = []

    for index, row in rows:
        excel_row = index + 2
        row_is_valid = True

        movement_date = _parse_date(row.get("Date"))
        if movement_date is None:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_date",
                    message=LocalisedMessage(
                        "Date is missing or invalid. Use a valid Excel date "
                        "(for example 2026-10-03)."
                    ),
                    sheet=STOCK_MOVEMENTS_SPEC.name,
                    row=excel_row,
                    column="Date",
                )
            )
            row_is_valid = False
        elif opening_date is not None and movement_date < opening_date:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="movement_before_opening",
                    message=LocalisedMessage(
                        "Movement date {movement_date} is before the Opening "
                        "Stock Date {opening_date}. Movements cannot predate the "
                        "opening balance.",
                        movement_date=movement_date.isoformat(),
                        opening_date=opening_date.isoformat(),
                    ),
                    sheet=STOCK_MOVEMENTS_SPEC.name,
                    row=excel_row,
                    column="Date",
                )
            )
            row_is_valid = False

        transaction_type = _text(row.get("Transaction Type")).upper()
        if transaction_type not in TRANSACTION_TYPES:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_transaction_type",
                    message=LocalisedMessage(
                        "Transaction Type must be IN or OUT. Received '{value}'.",
                        value=_text(row.get("Transaction Type")) or "blank",
                    ),
                    sheet=STOCK_MOVEMENTS_SPEC.name,
                    row=excel_row,
                    column="Transaction Type",
                )
            )
            row_is_valid = False

        quantity = _parse_integer(row.get("Quantity"))
        if quantity is None or quantity <= 0:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_quantity",
                    message=LocalisedMessage("Quantity must be a positive whole number."),
                    sheet=STOCK_MOVEMENTS_SPEC.name,
                    row=excel_row,
                    column="Quantity",
                )
            )
            row_is_valid = False

        if row_is_valid:
            movements.append(
                StockMovement(
                    date=movement_date,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    description=_text(row.get("Description")),
                )
            )

    return tuple(movements)


def _validate_open_orders(
    frame: pd.DataFrame,
    result: ValidationResult,
) -> tuple[OpenOrder, ...]:
    if not _check_columns(frame, OPEN_ORDERS_SPEC, result):
        return ()

    rows = list(_data_rows(frame))
    if not rows:
        result.issues.append(
            ValidationIssue(
                severity=WARNING,
                code="no_open_orders",
                message=LocalisedMessage(
                    "No open orders were found. The workbook is valid, but "
                    "incoming supply will not be included in later planning."
                ),
                sheet=OPEN_ORDERS_SPEC.name,
            )
        )
        return ()

    orders: list[OpenOrder] = []
    order_numbers: list[tuple[int, str]] = []

    for index, row in rows:
        excel_row = index + 2
        row_is_valid = True

        order_no = _text(row.get("Order No"))
        if not order_no:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="required_field",
                    message=LocalisedMessage("Order No is required."),
                    sheet=OPEN_ORDERS_SPEC.name,
                    row=excel_row,
                    column="Order No",
                )
            )
            row_is_valid = False
        else:
            order_numbers.append((excel_row, order_no))

        quantity = _parse_integer(row.get("Order Quantity"))
        if quantity is None or quantity <= 0:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_quantity",
                    message=LocalisedMessage("Order Quantity must be a positive whole number."),
                    sheet=OPEN_ORDERS_SPEC.name,
                    row=excel_row,
                    column="Order Quantity",
                )
            )
            row_is_valid = False

        delivery_date = _parse_date(row.get("Expected Delivery Date"))
        if delivery_date is None:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="invalid_date",
                    message=LocalisedMessage(
                        "Expected Delivery Date is missing or invalid. Use a "
                        "valid Excel date."
                    ),
                    sheet=OPEN_ORDERS_SPEC.name,
                    row=excel_row,
                    column="Expected Delivery Date",
                )
            )
            row_is_valid = False

        if row_is_valid:
            orders.append(
                OpenOrder(
                    order_no=order_no,
                    order_quantity=quantity,
                    expected_delivery_date=delivery_date,
                )
            )

    _check_duplicate_order_numbers(order_numbers, result)
    return tuple(orders)


def _check_duplicate_order_numbers(
    order_numbers: list[tuple[int, str]],
    result: ValidationResult,
) -> None:
    seen: dict[str, list[int]] = {}
    for excel_row, order_no in order_numbers:
        seen.setdefault(order_no.casefold(), []).append(excel_row)

    for rows in seen.values():
        if len(rows) > 1:
            result.issues.append(
                ValidationIssue(
                    severity=ERROR,
                    code="duplicate_order_no",
                    message=LocalisedMessage(
                        "Order No must be unique. Duplicate value found in "
                        "Excel rows: {rows}.",
                        rows=", ".join(map(str, rows)),
                    ),
                    sheet=OPEN_ORDERS_SPEC.name,
                    column="Order No",
                )
            )
