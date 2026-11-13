"""Validation tests for the Inventory Intelligence Excel contract."""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd

from config import DEMO_SOURCE
from core.excel_reader import read_workbook
from core.schema import SHEET_SPECS
from core.validation import ERROR, validate_excel, validate_excel_file


def _validate(payload: bytes, filename: str = "workbook.xlsx"):
    return validate_excel(BytesIO(payload), filename=filename)


def _copy_sheets(sheets: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: frame.copy() for name, frame in sheets.items()}


def test_valid_workbook_loads(valid_sheets, make_workbook):
    result = _validate(make_workbook(valid_sheets), filename="valid.xlsx")

    assert result.is_valid
    assert result.errors == []
    assert result.dataset is not None
    assert result.dataset.product.product_code == "SKU-001"
    assert result.dataset.product.opening_stock == 500
    assert result.dataset.movement_count == 3
    assert result.dataset.open_order_count == 2
    assert result.dataset.source == "upload"
    assert result.dataset.filename == "valid.xlsx"


def test_demo_workbook_is_valid(demo_path):
    result = validate_excel_file(demo_path, source_kind=DEMO_SOURCE)

    assert result.is_valid
    assert result.error_count == 0
    assert result.dataset is not None
    assert result.dataset.is_demo
    assert result.dataset.product.product_code == "PRF-4040-02"
    assert result.dataset.movement_count == 18
    assert result.dataset.open_order_count == 2


def test_template_headers_match_schema(template_path):
    sheets = read_workbook(template_path)

    for spec in SHEET_SPECS:
        assert spec.name in sheets
        assert tuple(sheets[spec.name].columns) == spec.required_columns


def test_empty_template_is_reported_without_crashing(template_path):
    result = validate_excel_file(template_path)

    assert not result.is_valid
    assert result.dataset is None
    assert any(issue.code == "empty_product_master" for issue in result.errors)


def test_missing_sheet_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    del sheets["Open Orders"]

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    issue = next(issue for issue in result.errors if issue.code == "missing_sheet")
    assert issue.sheet == "Open Orders"
    assert "Open Orders" in issue.message


def test_missing_column_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Product Master"] = sheets["Product Master"].drop(columns=["Safety Stock"])

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    issue = next(issue for issue in result.errors if issue.code == "missing_columns")
    assert issue.sheet == "Product Master"
    assert "Safety Stock" in issue.message


def test_invalid_transaction_type_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"].loc[0, "Transaction Type"] = "ADJUST"

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    issue = next(
        issue for issue in result.errors if issue.code == "invalid_transaction_type"
    )
    assert issue.sheet == "Stock Movements"
    assert issue.row == 2
    assert issue.column == "Transaction Type"


def test_negative_quantity_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"].loc[0, "Quantity"] = -5

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    issue = next(issue for issue in result.errors if issue.code == "invalid_quantity")
    assert issue.row == 2
    assert issue.column == "Quantity"


def test_zero_quantity_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Open Orders"].loc[0, "Order Quantity"] = 0

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    assert any(
        issue.code == "invalid_quantity" and issue.sheet == "Open Orders"
        for issue in result.errors
    )


def test_non_integer_quantity_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    quantities = sheets["Stock Movements"]["Quantity"].astype(float)
    quantities.loc[0] = 12.5
    sheets["Stock Movements"]["Quantity"] = quantities

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    assert any(
        issue.code == "invalid_quantity" and issue.row == 2
        for issue in result.errors
    )


def test_movement_before_opening_date_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"].loc[0, "Date"] = date(2026, 9, 30)

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    issue = next(
        issue for issue in result.errors if issue.code == "movement_before_opening"
    )
    assert issue.row == 2
    assert "2026-09-30" in issue.message
    assert "2026-10-01" in issue.message


def test_invalid_date_is_reported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"].loc[0, "Date"] = "not-a-date"

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    issue = next(issue for issue in result.errors if issue.code == "invalid_date")
    assert issue.sheet == "Stock Movements"
    assert issue.row == 2


def test_multiple_products_are_rejected(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    extra_product = sheets["Product Master"].copy()
    extra_product.loc[0, "Product Code"] = "SKU-002"
    sheets["Product Master"] = pd.concat(
        [sheets["Product Master"], extra_product], ignore_index=True
    )

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    assert any(issue.code == "multiple_products" for issue in result.errors)
    assert result.dataset is None


def test_duplicate_product_code_is_rejected(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Product Master"] = pd.concat(
        [sheets["Product Master"], sheets["Product Master"]], ignore_index=True
    )

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    assert any(issue.code == "duplicate_product_code" for issue in result.errors)


def test_duplicate_order_number_is_rejected(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Open Orders"].loc[1, "Order No"] = "PO-001"

    result = _validate(make_workbook(sheets))

    assert not result.is_valid
    assert any(issue.code == "duplicate_order_no" for issue in result.errors)


def test_empty_movements_is_a_warning_not_an_error(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"] = sheets["Stock Movements"].iloc[0:0]

    result = _validate(make_workbook(sheets))

    assert result.is_valid
    assert result.dataset is not None
    assert result.dataset.movements == ()
    assert any(issue.code == "no_movements" for issue in result.warnings)


def test_zero_opening_stock_is_allowed(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Product Master"].loc[0, "Opening Stock"] = 0

    result = _validate(make_workbook(sheets))

    assert result.is_valid


def test_transaction_type_is_case_insensitive(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"].loc[0, "Transaction Type"] = "out"

    result = _validate(make_workbook(sheets))

    assert result.is_valid
    assert result.dataset is not None
    assert result.dataset.movements[0].transaction_type == "OUT"


def test_text_dates_are_supported(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Stock Movements"].loc[0, "Date"] = "2026-10-03"

    result = _validate(make_workbook(sheets))

    assert result.is_valid


def test_unreadable_file_is_reported_without_crashing():
    result = _validate(b"this is not an excel workbook", filename="broken.xlsx")

    assert not result.is_valid
    assert result.dataset is None
    assert result.errors[0].code == "file_unreadable"
    assert result.errors[0].severity == ERROR


def test_extra_columns_produce_a_warning(valid_sheets, make_workbook):
    sheets = _copy_sheets(valid_sheets)
    sheets["Product Master"]["Notes"] = "optional"

    result = _validate(make_workbook(sheets))

    assert result.is_valid
    assert any(issue.code == "unexpected_columns" for issue in result.warnings)
