"""Shared pytest fixtures for workbook validation tests."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_workbook(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()


@pytest.fixture
def template_path() -> Path:
    return PROJECT_ROOT / "templates" / "inventory-intelligence-template.xlsx"


@pytest.fixture
def demo_path() -> Path:
    return PROJECT_ROOT / "templates" / "inventory-intelligence-demo.xlsx"


@pytest.fixture
def valid_sheets() -> dict[str, pd.DataFrame]:
    return {
        "Product Master": pd.DataFrame(
            [
                {
                    "Product Code": "SKU-001",
                    "Product Name": "Steel Profile 40x40",
                    "Unit": "pcs",
                    "Opening Stock": 500,
                    "Opening Stock Date": date(2026, 10, 1),
                    "Safety Stock": 100,
                    "Lead Time Days": 12,
                    "Target Coverage Days": 20,
                }
            ]
        ),
        "Stock Movements": pd.DataFrame(
            [
                {
                    "Date": date(2026, 10, 3),
                    "Transaction Type": "OUT",
                    "Quantity": 18,
                    "Description": "Production consumption",
                },
                {
                    "Date": date(2026, 10, 7),
                    "Transaction Type": "IN",
                    "Quantity": 100,
                    "Description": "Supplier delivery",
                },
                {
                    "Date": date(2026, 10, 10),
                    "Transaction Type": "OUT",
                    "Quantity": 25,
                    "Description": "Production consumption",
                },
            ]
        ),
        "Open Orders": pd.DataFrame(
            [
                {
                    "Order No": "PO-001",
                    "Order Quantity": 200,
                    "Expected Delivery Date": date(2026, 11, 18),
                },
                {
                    "Order No": "PO-002",
                    "Order Quantity": 100,
                    "Expected Delivery Date": date(2026, 11, 25),
                },
            ]
        ),
    }


@pytest.fixture
def make_workbook():
    return _build_workbook
