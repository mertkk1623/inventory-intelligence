"""Blank template and richly instrumented sample workbooks.

Everything in this module is generated from :mod:`core.schema`, so the
column names can never drift away from the validator contract. Two products
are offered:

``blank_template_bytes``
    A ready-to-fill workbook with the exact required sheets, the exact column
    headers and a ``Read Me`` sheet that explains every column and format rule.

``sample_workbook_bytes``
    A fully populated, validator-clean workbook for one of the curated demo
    scenarios. Every scenario is deliberately constructed so the deterministic
    engine produces a specific, explainable signal (stockout risk, dead stock,
    a negative running balance, a high-velocity mover), which in turn gives the
    AI layer something concrete to interpret.

The module is deliberately free of Streamlit imports so the test suite, the
CLI tools and the report builders can use it directly. Dates are anchored to a
reference date (today by default) rather than hard-coded, so the bundled
scenarios never expire and are always treated as a *current* report.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from core.schema import SHEET_SPECS

# The demo history opens this many days before the reference date, and the
# consumption window is the standard rolling 30-day window used by the engine.
OPENING_OFFSET_DAYS = 61
READ_ME_SHEET = "Read Me"

GUIDE_ROWS: tuple[tuple[str, str], ...] = (
    (
        "Inventory Intelligence — data template",
        "Fill in the three data sheets. Keep every sheet name and column "
        "header exactly as provided; the validator rejects renamed sheets or "
        "columns.",
    ),
    (
        "Product Master",
        "Exactly one row describing your single SKU. V1 supports one product "
        "and one warehouse per workbook.",
    ),
    (
        "Product Code",
        "Unique SKU identifier. Required, for example SKU-IND-1042.",
    ),
    (
        "Product Name",
        "Readable product name. Required.",
    ),
    (
        "Unit",
        "Unit of measure such as Adet, pcs, kg or m. Required.",
    ),
    (
        "Opening Stock",
        "Stock on hand at the Opening Stock Date. Whole number, 0 or greater.",
    ),
    (
        "Opening Stock Date",
        "Start of the movement history, as a real Excel date (YYYY-MM-DD). No "
        "movement may be dated before it.",
    ),
    (
        "Safety Stock",
        "Minimum planning buffer. Whole number, 0 or greater. The engine keeps "
        "it in the reorder point and target stock formulas.",
    ),
    (
        "Lead Time Days",
        "Supplier lead time in calendar days. Whole number, 0 or greater.",
    ),
    (
        "Target Coverage Days",
        "Days of demand the target stock should cover on top of the lead time. "
        "Whole number, 1 or greater.",
    ),
    (
        "Stock Movements",
        "One row per IN or OUT transaction dated on or after the Opening Stock "
        "Date.",
    ),
    (
        "Date",
        "Movement date as a real Excel date (YYYY-MM-DD). Required.",
    ),
    (
        "Transaction Type",
        "IN for a receipt, OUT for consumption or shipment. Case-insensitive, "
        "but only these two values are accepted.",
    ),
    (
        "Quantity",
        "Movement quantity as a positive whole number. Zero and negatives are "
        "rejected.",
    ),
    (
        "Description",
        "Short free-text note. Optional. Long text is truncated before it is "
        "sent to the AI provider.",
    ),
    (
        "Open Orders",
        "Purchase orders placed but not yet delivered. One row per order.",
    ),
    (
        "Order No",
        "Unique order number. Required; duplicates are rejected.",
    ),
    (
        "Order Quantity",
        "Ordered quantity as a positive whole number.",
    ),
    (
        "Expected Delivery Date",
        "Promised delivery date as a real Excel date (YYYY-MM-DD). A date "
        "before the report date is counted as an overdue order.",
    ),
    (
        "Format rules",
        "Dates must be real Excel dates. Transaction Type must be IN or OUT. "
        "Quantities must be positive whole numbers. Opening Stock and Safety "
        "Stock must be 0 or greater. Product codes and order numbers must be "
        "unique.",
    ),
)


@dataclass(frozen=True)
class SampleScenario:
    """One curated demo scenario.

    Movement and order offsets are expressed in days from the opening date, so
    a scenario keeps its shape no matter when it is generated.
    """

    key: str
    name: str
    summary: str
    product_code: str
    product_name: str
    unit: str
    opening_stock: int
    safety_stock: int
    lead_time_days: int
    target_coverage_days: int
    movements: tuple[tuple[int, str, int, str], ...]
    orders: tuple[tuple[str, int, int], ...] = ()

    @property
    def movement_count(self) -> int:
        return len(self.movements)

    @property
    def order_count(self) -> int:
        return len(self.orders)

    def opening_date(self, reference: date) -> date:
        return reference - timedelta(days=OPENING_OFFSET_DAYS)

    def product_row(self, reference: date) -> dict[str, object]:
        return {
            "Product Code": self.product_code,
            "Product Name": self.product_name,
            "Unit": self.unit,
            "Opening Stock": self.opening_stock,
            "Opening Stock Date": self.opening_date(reference),
            "Safety Stock": self.safety_stock,
            "Lead Time Days": self.lead_time_days,
            "Target Coverage Days": self.target_coverage_days,
        }

    def movement_rows(self, reference: date) -> list[dict[str, object]]:
        opening = self.opening_date(reference)
        return [
            {
                "Date": opening + timedelta(days=offset),
                "Transaction Type": transaction_type,
                "Quantity": quantity,
                "Description": description,
            }
            for offset, transaction_type, quantity, description in self.movements
        ]

    def order_rows(self, reference: date) -> list[dict[str, object]]:
        opening = self.opening_date(reference)
        return [
            {
                "Order No": order_no,
                "Order Quantity": quantity,
                "Expected Delivery Date": opening + timedelta(days=offset),
            }
            for order_no, quantity, offset in self.orders
        ]

    def sheets(self, reference: date) -> dict[str, pd.DataFrame]:
        """Return the three data sheets as DataFrames with schema columns."""

        frames: dict[str, pd.DataFrame] = {}
        for spec in SHEET_SPECS:
            if spec.name == "Product Master":
                frames[spec.name] = pd.DataFrame(
                    [self.product_row(reference)], columns=list(spec.required_columns)
                )
            elif spec.name == "Stock Movements":
                frames[spec.name] = pd.DataFrame(
                    self.movement_rows(reference),
                    columns=list(spec.required_columns),
                )
            elif spec.name == "Open Orders":
                frames[spec.name] = pd.DataFrame(
                    self.order_rows(reference), columns=list(spec.required_columns)
                )
        return frames


# ---------------------------------------------------------------------------
# Scenario catalogue
# ---------------------------------------------------------------------------

# 1. Critical stockout: steady demand, then a seasonal ramp while supply stays
#    flat, one overdue purchase order and one imminent delivery.
_STOCKOUT_MOVEMENTS: tuple[tuple[int, str, int, str], ...] = (
    (2, "OUT", 18, "Assembly line consumption"),
    (4, "OUT", 21, "Assembly line consumption"),
    (6, "OUT", 16, "Assembly line consumption"),
    (8, "OUT", 19, "Assembly line consumption"),
    (10, "OUT", 23, "Assembly line consumption"),
    (12, "OUT", 17, "Assembly line consumption"),
    (14, "OUT", 20, "Assembly line consumption"),
    (16, "OUT", 22, "Assembly line consumption"),
    (18, "OUT", 18, "Assembly line consumption"),
    (19, "IN", 220, "Scheduled supplier delivery"),
    (20, "OUT", 24, "Assembly line consumption"),
    (22, "OUT", 26, "Assembly line consumption"),
    (24, "OUT", 21, "Assembly line consumption"),
    (26, "OUT", 25, "Assembly line consumption"),
    (28, "OUT", 27, "Assembly line consumption"),
    (30, "OUT", 24, "Assembly line consumption"),
    (32, "OUT", 29, "Demand ramps up ahead of the seasonal campaign"),
    (34, "OUT", 32, "Demand ramps up ahead of the seasonal campaign"),
    (36, "OUT", 34, "Seasonal campaign consumption"),
    (38, "OUT", 36, "Seasonal campaign consumption"),
    (40, "OUT", 38, "Seasonal campaign consumption"),
    (41, "IN", 40, "Partial emergency delivery"),
    (42, "OUT", 35, "Seasonal campaign consumption"),
    (44, "OUT", 33, "Seasonal campaign consumption"),
    (46, "OUT", 31, "Seasonal campaign consumption"),
    (47, "OUT", 29, "Seasonal campaign consumption"),
    (49, "OUT", 32, "Seasonal campaign consumption"),
    (51, "OUT", 28, "Seasonal campaign consumption"),
    (53, "OUT", 30, "Seasonal campaign consumption"),
    (55, "OUT", 27, "Seasonal campaign consumption"),
    (57, "OUT", 31, "Seasonal campaign consumption"),
    (59, "OUT", 26, "Seasonal campaign consumption"),
    (61, "OUT", 29, "Seasonal campaign consumption"),
)

# 2. Dead stock: a long, quiet history and almost no recent demand, so several
#    thousand units of working capital sit idle with an enormous days-of-supply.
_DEAD_STOCK_MOVEMENTS: tuple[tuple[int, str, int, str], ...] = (
    (2, "OUT", 14, "Legacy line service demand"),
    (3, "OUT", 11, "Legacy line service demand"),
    (5, "OUT", 19, "Legacy line service demand"),
    (6, "OUT", 12, "Legacy line service demand"),
    (8, "OUT", 16, "Legacy line service demand"),
    (9, "OUT", 10, "Legacy line service demand"),
    (11, "OUT", 18, "Legacy line service demand"),
    (12, "OUT", 15, "Legacy line service demand"),
    (14, "OUT", 13, "Legacy line service demand"),
    (15, "OUT", 21, "Legacy line service demand"),
    (17, "OUT", 17, "Legacy line service demand"),
    (18, "OUT", 12, "Legacy line service demand"),
    (20, "OUT", 16, "Legacy line service demand"),
    (21, "OUT", 19, "Legacy line service demand"),
    (23, "OUT", 14, "Legacy line service demand"),
    (24, "OUT", 11, "Legacy line service demand"),
    (26, "OUT", 18, "Legacy line service demand"),
    (27, "OUT", 15, "Legacy line service demand"),
    (29, "OUT", 13, "Legacy line service demand"),
    (30, "OUT", 20, "Legacy line service demand"),
    (32, "OUT", 17, "Final production run for the legacy line"),
    (33, "OUT", 22, "Final production run for the legacy line"),
    (35, "OUT", 16, "Final production run for the legacy line"),
    (36, "IN", 200, "Residual supplier delivery"),
    (37, "OUT", 14, "Final production run for the legacy line"),
    (39, "OUT", 18, "Final production run for the legacy line"),
    (41, "OUT", 12, "Final production run for the legacy line"),
    (44, "OUT", 9, "Line decommissioned, demand winds down"),
    (47, "OUT", 4, "Line decommissioned, demand winds down"),
    (50, "OUT", 2, "Spare-part request"),
    (53, "OUT", 1, "Spare-part request"),
    (56, "OUT", 2, "Spare-part request"),
    (59, "OUT", 1, "Spare-part request"),
    (61, "OUT", 1, "Spare-part request"),
)

# 3. Negative balance: a bulk project shipment is picked before its confirming
#    receipt is recorded, so the running balance dips below zero and recovers.
_NEGATIVE_MOVEMENTS: tuple[tuple[int, str, int, str], ...] = (
    (2, "OUT", 12, "Project assembly consumption"),
    (4, "OUT", 15, "Project assembly consumption"),
    (6, "OUT", 11, "Project assembly consumption"),
    (8, "OUT", 650, "Bulk shipment picked before the receipt was posted"),
    (10, "OUT", 18, "Project assembly consumption"),
    (12, "IN", 900, "Receipt posted, backlog corrected"),
    (14, "OUT", 24, "Project assembly consumption"),
    (16, "OUT", 19, "Project assembly consumption"),
    (18, "OUT", 22, "Project assembly consumption"),
    (20, "OUT", 16, "Project assembly consumption"),
    (22, "OUT", 25, "Project assembly consumption"),
    (24, "OUT", 21, "Project assembly consumption"),
    (26, "OUT", 18, "Project assembly consumption"),
    (28, "OUT", 23, "Project assembly consumption"),
    (30, "OUT", 20, "Project assembly consumption"),
    (32, "OUT", 26, "Project assembly consumption"),
    (34, "OUT", 24, "Project assembly consumption"),
    (36, "OUT", 19, "Project assembly consumption"),
    (38, "OUT", 27, "Project assembly consumption"),
    (40, "OUT", 22, "Project assembly consumption"),
    (42, "OUT", 25, "Project assembly consumption"),
    (44, "OUT", 21, "Project assembly consumption"),
    (46, "OUT", 23, "Project assembly consumption"),
    (48, "OUT", 18, "Project assembly consumption"),
    (50, "OUT", 20, "Project assembly consumption"),
    (52, "OUT", 24, "Project assembly consumption"),
    (54, "OUT", 22, "Project assembly consumption"),
    (56, "OUT", 19, "Project assembly consumption"),
    (58, "OUT", 21, "Project assembly consumption"),
    (61, "OUT", 17, "Project assembly consumption"),
)

# 4. Fast mover: high daily turnover, healthy cover above the reorder point,
#    and a scheduled delivery. This is the low-risk contrast to dead stock.
_FAST_MOVER_MOVEMENTS: tuple[tuple[int, str, int, str], ...] = (
    (1, "OUT", 46, "Production line consumption"),
    (2, "OUT", 51, "Production line consumption"),
    (4, "OUT", 55, "Production line consumption"),
    (5, "OUT", 48, "Production line consumption"),
    (7, "OUT", 53, "Production line consumption"),
    (8, "OUT", 60, "Production line consumption"),
    (10, "OUT", 44, "Production line consumption"),
    (11, "OUT", 58, "Production line consumption"),
    (13, "OUT", 50, "Production line consumption"),
    (14, "OUT", 47, "Production line consumption"),
    (16, "OUT", 54, "Production line consumption"),
    (17, "OUT", 49, "Production line consumption"),
    (18, "IN", 800, "Scheduled supplier delivery"),
    (19, "OUT", 52, "Production line consumption"),
    (21, "OUT", 57, "Production line consumption"),
    (22, "OUT", 50, "Production line consumption"),
    (24, "OUT", 55, "Production line consumption"),
    (25, "OUT", 61, "Production line consumption"),
    (28, "OUT", 54, "Production line consumption"),
    (30, "OUT", 58, "Production line consumption"),
    (32, "OUT", 62, "Production line consumption"),
    (34, "OUT", 57, "Production line consumption"),
    (36, "OUT", 66, "Production line consumption"),
    (38, "OUT", 60, "Production line consumption"),
    (40, "OUT", 64, "Production line consumption"),
    (43, "OUT", 58, "Production line consumption"),
    (46, "OUT", 68, "Production line consumption"),
    (47, "IN", 400, "Scheduled supplier delivery"),
    (49, "OUT", 63, "Production line consumption"),
    (52, "OUT", 70, "Production line consumption"),
    (55, "OUT", 66, "Production line consumption"),
    (58, "OUT", 72, "Production line consumption"),
    (61, "OUT", 65, "Production line consumption"),
)

SAMPLE_SCENARIOS: tuple[SampleScenario, ...] = (
    SampleScenario(
        key="stockout",
        name="Stockout risk",
        summary=(
            "Demand ramps up for a seasonal campaign while supply stays flat. "
            "Stock is far below safety stock, the position is under the reorder "
            "point and one purchase order is already overdue."
        ),
        product_code="SKU-IND-1042",
        product_name="Industrial Bearing 6205-2RS",
        unit="Adet",
        opening_stock=620,
        safety_stock=300,
        lead_time_days=21,
        target_coverage_days=30,
        movements=_STOCKOUT_MOVEMENTS,
        orders=(
            ("PO-7781", 150, 58),
            ("PO-7782", 120, 70),
        ),
    ),
    SampleScenario(
        key="dead_stock",
        name="Dead stock",
        summary=(
            "A legacy part with almost no demand for two months. Several "
            "thousand units of working capital are tied up and days of supply "
            "runs into the thousands."
        ),
        product_code="SKU-LEG-2087",
        product_name="Legacy Hydraulic Valve HV-22",
        unit="Adet",
        opening_stock=4800,
        safety_stock=150,
        lead_time_days=35,
        target_coverage_days=60,
        movements=_DEAD_STOCK_MOVEMENTS,
        orders=(("PO-5501", 100, 72),),
    ),
    SampleScenario(
        key="negative_stock",
        name="Negative stock",
        summary=(
            "A bulk project shipment is picked before its confirming receipt is "
            "posted. The running balance drops below zero and recovers, which "
            "exercises the negative stock alert and the data-quality caveat."
        ),
        product_code="SKU-PRJ-7001",
        product_name="Project Cable Harness CH-12",
        unit="Adet",
        opening_stock=400,
        safety_stock=200,
        lead_time_days=14,
        target_coverage_days=21,
        movements=_NEGATIVE_MOVEMENTS,
        orders=(("PO-9004", 300, 66),),
    ),
    SampleScenario(
        key="fast_mover",
        name="Fast mover",
        summary=(
            "A high-velocity component with steady daily consumption, healthy "
            "cover above the reorder point and one scheduled delivery. The "
            "contrast to dead stock is what ABC classification would care about."
        ),
        product_code="SKU-FST-5001",
        product_name="Production Line Sensor PL-7",
        unit="Adet",
        opening_stock=2400,
        safety_stock=300,
        lead_time_days=10,
        target_coverage_days=15,
        movements=_FAST_MOVER_MOVEMENTS,
        orders=(("PO-4410", 400, 72),),
    ),
)

SCENARIO_KEYS: tuple[str, ...] = tuple(scenario.key for scenario in SAMPLE_SCENARIOS)
DEFAULT_SCENARIO_KEY = "stockout"

_SCENARIOS_BY_KEY: dict[str, SampleScenario] = {
    scenario.key: scenario for scenario in SAMPLE_SCENARIOS
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_scenario(key: str) -> SampleScenario:
    """Return the scenario registered under ``key``.

    Raises:
        ValueError: if the key is unknown, so a typo in the UI cannot silently
            fall back to a different dataset.
    """

    try:
        return _SCENARIOS_BY_KEY[key]
    except KeyError:
        raise ValueError(
            f"Unknown sample scenario '{key}'. Available: "
            + ", ".join(SCENARIO_KEYS)
        ) from None


def sample_filename(key: str) -> str:
    """Return the download filename for a scenario workbook."""

    scenario = get_scenario(key)
    return f"inventory-intelligence-demo-{scenario.key}.xlsx"


BLANK_TEMPLATE_FILENAME = "inventory-intelligence-blank-template.xlsx"


def blank_template_sheets() -> dict[str, pd.DataFrame]:
    """Return the three empty data sheets with their exact schema headers."""

    return {
        spec.name: pd.DataFrame(columns=list(spec.required_columns))
        for spec in SHEET_SPECS
    }


def blank_template_bytes() -> bytes:
    """Return the empty, format-guided template workbook as xlsx bytes."""

    return _build_workbook(blank_template_sheets(), validate_input=True)


def sample_workbook_bytes(key: str, *, reference: date | None = None) -> bytes:
    """Return a populated scenario workbook as xlsx bytes."""

    scenario = get_scenario(key)
    anchor = reference or date.today()
    return _build_workbook(scenario.sheets(anchor), validate_input=True)


def sample_workbook_path(
    key: str,
    *,
    reference: date | None = None,
    directory: str | Path | None = None,
) -> Path:
    """Write a scenario workbook to disk and return its path.

    This is a convenience for scripts and manual checks; the Streamlit app
    generates the bytes in memory and never touches the filesystem.
    """

    from tempfile import gettempdir

    target_dir = Path(directory) if directory is not None else Path(gettempdir())
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / sample_filename(key)
    path.write_bytes(sample_workbook_bytes(key, reference=reference))
    return path


# ---------------------------------------------------------------------------
# Workbook construction
# ---------------------------------------------------------------------------


def _build_workbook(sheets: dict[str, pd.DataFrame], *, validate_input: bool) -> bytes:
    buffer = BytesIO()
    guide = pd.DataFrame(GUIDE_ROWS, columns=["Topic", "Guidance"])

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for spec in SHEET_SPECS:
            frame = sheets.get(spec.name)
            if frame is None:
                frame = pd.DataFrame(columns=list(spec.required_columns))
            frame.to_excel(writer, sheet_name=spec.name, index=False)
        guide.to_excel(writer, sheet_name=READ_ME_SHEET, index=False)
        _style_workbook(writer.book, validate_input=validate_input)

    return buffer.getvalue()


def _style_workbook(workbook, *, validate_input: bool) -> None:
    """Apply light formatting so the generated workbook is pleasant to edit."""

    header_fill = PatternFill("solid", fgColor="14243A")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(color="14243A", bold=True, size=12)
    wrap = Alignment(wrap_text=True, vertical="top")

    for spec in SHEET_SPECS:
        sheet = workbook[spec.name]
        for column_index, name in enumerate(spec.required_columns, start=1):
            cell = sheet.cell(row=1, column=column_index)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(vertical="center")
            width = max(14, min(34, len(name) + 8))
            sheet.column_dimensions[cell.column_letter].width = width
        sheet.freeze_panes = "A2"
        _add_transaction_type_validation(sheet, spec.name, validate_input)

    guide = workbook[READ_ME_SHEET]
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 96
    for row in guide.iter_rows(min_row=1, max_row=guide.max_row, max_col=2):
        for cell in row:
            cell.alignment = wrap
    for cell in guide["A"]:
        cell.font = title_font
    guide.freeze_panes = "A2"


def _add_transaction_type_validation(sheet, sheet_name: str, enabled: bool) -> None:
    """Restrict Transaction Type to IN/OUT with a dropdown."""

    if not enabled or sheet_name != "Stock Movements":
        return

    validation = DataValidation(
        type="list",
        formula1='"IN,OUT"',
        allow_blank=True,
        showDropDown=False,
    )
    validation.error = "Use IN for a receipt or OUT for consumption."
    validation.errorTitle = "Transaction Type"
    validation.prompt = "Choose IN or OUT."
    validation.promptTitle = "Transaction Type"
    sheet.add_data_validation(validation)
    validation.add(f"B2:B{max(2, sheet.max_row + 200)}")


@lru_cache(maxsize=8)
def _cached_sample_bytes(key: str, reference_iso: str) -> bytes:
    return sample_workbook_bytes(key, reference=date.fromisoformat(reference_iso))


@lru_cache(maxsize=1)
def _cached_blank_template() -> bytes:
    return blank_template_bytes()


def cached_sample_workbook_bytes(
    key: str,
    *,
    reference: date | None = None,
) -> bytes:
    """Return cached scenario bytes for a given calendar day.

    Generating a workbook is cheap but not free, and the welcome screen renders
    on every rerun. Caching by scenario and day keeps the download button fast
    without ever serving a stale date anchor.
    """

    anchor = reference or date.today()
    return _cached_sample_bytes(key, anchor.isoformat())


def cached_blank_template_bytes() -> bytes:
    """Return the cached blank template workbook bytes."""

    return _cached_blank_template()


__all__ = [
    "BLANK_TEMPLATE_FILENAME",
    "DEFAULT_SCENARIO_KEY",
    "GUIDE_ROWS",
    "READ_ME_SHEET",
    "SAMPLE_SCENARIOS",
    "SCENARIO_KEYS",
    "SampleScenario",
    "blank_template_bytes",
    "blank_template_sheets",
    "cached_blank_template_bytes",
    "cached_sample_workbook_bytes",
    "get_scenario",
    "sample_filename",
    "sample_workbook_bytes",
    "sample_workbook_path",
]
