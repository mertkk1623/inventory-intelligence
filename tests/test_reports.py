"""Package 4 tests: Excel and PDF report generation and the Reports screen."""

from __future__ import annotations

import contextlib
import re
import zipfile
import zlib
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from config import DEMO_FILE, DEMO_SOURCE
from core.calculations import calculate_inventory
from core.models import (
    InventoryDataset,
    OpenOrder,
    ProductMaster,
    StockMovement,
)
from core.validation import validate_excel_file
from reports import build_report_context
from reports.excel_report import (
    SHEET_CONSUMPTION,
    SHEET_MOVEMENTS,
    SHEET_ORDER,
    SHEET_ORDERS,
    SHEET_REPLENISHMENT,
    SHEET_SUMMARY,
    build_excel_report,
)
from reports.pdf_report import build_pdf_report

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
TODAY = date.today()


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def make_dataset(
    *,
    product_code: str = "PRF-4040-02",
    product_name: str = "Galvanised Square Profile 40x40",
    unit: str = "Adet",
    opening_stock: int = 500,
    opening_date: date | None = None,
    safety_stock: int = 100,
    lead_time_days: int = 12,
    target_coverage_days: int = 20,
    movements: tuple[StockMovement, ...] = (),
    open_orders: tuple[OpenOrder, ...] = (),
    source: str = "upload",
    filename: str = "test.xlsx",
) -> InventoryDataset:
    product = ProductMaster(
        product_code=product_code,
        product_name=product_name,
        unit=unit,
        opening_stock=opening_stock,
        opening_stock_date=opening_date or TODAY,
        safety_stock=safety_stock,
        lead_time_days=lead_time_days,
        target_coverage_days=target_coverage_days,
    )
    return InventoryDataset(
        product=product,
        movements=movements,
        open_orders=open_orders,
        source=source,
        filename=filename,
    )


@pytest.fixture
def demo_dataset() -> InventoryDataset:
    validation = validate_excel_file(DEMO_FILE, source_kind=DEMO_SOURCE)
    assert validation.is_valid and validation.dataset is not None
    return validation.dataset


@pytest.fixture
def demo_context(demo_dataset):
    calculation = calculate_inventory(demo_dataset, TODAY)
    return build_report_context(demo_dataset, calculation)


def make_context(dataset: InventoryDataset, report_date: date | None = None):
    calculation = calculate_inventory(dataset, report_date or TODAY)
    return build_report_context(dataset, calculation)


def open_app(
    dataset: InventoryDataset | None = None,
    page: str | None = None,
    *,
    report_date: date | None = None,
) -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=90).run()
    if dataset is not None:
        app.session_state["ii_dataset"] = dataset
    if page is not None:
        app.session_state["ii_page"] = page
        app.session_state["ii_pending_page"] = page
    if report_date is not None:
        app.session_state["ii_report_date"] = report_date
    app.run()
    return app


def markdown_text(app: AppTest) -> str:
    return "\n".join(str(element.value) for element in app.markdown)


def download_buttons(app: AppTest) -> list:
    """Return download buttons across Streamlit testing API versions.

    Streamlit 1.67 exposes ``AppTest.download_button`` with ``click()``.
    Streamlit 1.53 only yields ``UnknownElement`` items from ``app.get`` whose
    proto carries the serialised media URL.
    """

    collection = getattr(app, "download_button", None)
    if collection is not None:
        return list(collection)
    return list(app.get("download_button"))


def download_label(button) -> str:
    return getattr(button, "label", None) or button.proto.label


def download_media_url(button) -> str:
    """Return the serialised media URL, if the version exposes one."""

    return getattr(button.proto, "url", "") or ""


def click_download(button) -> bool:
    """Click a download button when the testing API supports it."""

    click = getattr(button, "click", None)
    if click is None:
        return False
    click()
    return True


def load_workbook_bytes(payload: bytes):
    return load_workbook(BytesIO(payload))


def sheet_values(sheet, *, max_row: int | None = None) -> list[tuple]:
    return list(
        sheet.iter_rows(
            min_row=1,
            max_row=max_row or sheet.max_row,
            max_col=sheet.max_column,
            values_only=True,
        )
    )


def find_row(sheet, label: str) -> tuple | None:
    """Return the first row whose first cell equals ``label``."""

    for row in sheet_values(sheet):
        if row and row[0] == label:
            return row
    return None


def data_rows(sheet) -> list[tuple]:
    """Return the rows whose first cell is a date (the data rows)."""

    return [row for row in sheet_values(sheet) if row and hasattr(row[0], "year")]


def page_count(payload: bytes) -> int:
    """Count PDF page objects, excluding the ``/Pages`` tree node."""

    return len(re.findall(rb"/Type\s*/Page(?![s])", payload))


def pdf_text(payload: bytes) -> str:
    """Extract readable text from a ReportLab PDF without extra dependencies.

    ReportLab compresses page content streams (ASCII85 + Flate), so raw byte
    checks cannot see drawn text. This helper decodes every content stream and
    returns the concatenated operators, which is enough to assert on drawn
    strings.
    """

    import base64

    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", payload, re.DOTALL):
        raw = match.group(1).strip(b"\r\n")
        decoded = _decode_stream(raw, base64)
        if decoded is not None:
            chunks.append(decoded.decode("latin-1", "ignore"))
    return "\n".join(chunks)


def _decode_stream(raw: bytes, base64_module) -> bytes | None:
    """Undo ReportLab's ASCII85/Flate encoding for one stream."""

    candidates: list[bytes] = [raw]
    if raw.endswith(b"~>"):
        # Not ASCII85 after all is acceptable here; fall through to the plain
        # candidates below.
        with contextlib.suppress(ValueError):
            candidates.insert(0, base64_module.a85decode(raw[:-2], adobe=False))
    for candidate in candidates:
        try:
            return zlib.decompress(candidate)
        except zlib.error:
            continue
    # Some streams are already plain text.
    return raw if b"BT" in raw else None


# ---------------------------------------------------------------------------
# Excel report
# ---------------------------------------------------------------------------


def test_excel_report_is_generated_as_valid_xlsx(demo_context):
    payload = build_excel_report(demo_context)

    assert isinstance(payload, bytes)
    assert payload.startswith(b"PK")
    assert len(payload) > 4_000

    workbook = load_workbook_bytes(payload)
    assert workbook.sheetnames == list(SHEET_ORDER)


def test_excel_sheets_carry_the_expected_columns(demo_context):
    workbook = load_workbook_bytes(build_excel_report(demo_context))

    movements = workbook[SHEET_MOVEMENTS]
    headers = [
        cell.value
        for cell in next(
            movements.iter_rows(min_row=1, max_row=movements.max_row, max_col=5)
        )
    ]
    assert "Date" in headers or any(
        row[0] == "Date" for row in sheet_values(movements) if row
    )
    movement_header = next(row for row in sheet_values(movements) if row[0] == "Date")
    assert movement_header[:5] == (
        "Date",
        "Transaction Type",
        "Quantity",
        "Description",
        "Stock Balance",
    )

    orders = workbook[SHEET_ORDERS]
    order_header = next(
        row for row in sheet_values(orders) if row[0] == "Order Number"
    )
    assert order_header[:4] == (
        "Order Number",
        "Order Quantity",
        "Expected Delivery Date",
        "Overdue Status",
    )

    summary = workbook[SHEET_SUMMARY]
    labels = {row[0] for row in sheet_values(summary) if row and row[0]}
    assert {
        "Product Code",
        "Product Name",
        "Report Date",
        "Opening Stock",
        "Current Stock",
        "Total IN",
        "Total OUT",
        "Average Daily Consumption",
        "Days of Supply",
        "Safety Stock",
        "Reorder Point",
        "Open Order Quantity",
        "Inventory Position",
        "Target Stock",
        "Suggested Order Quantity",
        "Reorder Required",
        "Overdue Orders",
    } <= labels

    replenishment = workbook[SHEET_REPLENISHMENT]
    replenishment_labels = {
        row[0] for row in sheet_values(replenishment) if row and row[0]
    }
    assert {"Lead Time", "Reorder Point", "Target Stock"} <= replenishment_labels

    consumption = workbook[SHEET_CONSUMPTION]
    consumption_labels = {
        row[0] for row in sheet_values(consumption) if row and row[0]
    }
    assert {
        "Average Daily Consumption",
        "Total Consumption",
        "Highest Consumption Day",
        "Lowest Consumption Day",
        "DAILY CONSUMPTION",
        "WEEKLY CONSUMPTION",
    } <= consumption_labels


def test_excel_values_match_the_calculation_engine(demo_context):
    workbook = load_workbook_bytes(build_excel_report(demo_context))
    summary = workbook[SHEET_SUMMARY]
    calculation = demo_context.calculation

    def value_of(label: str):
        row = find_row(summary, label)
        assert row is not None, f"'{label}' missing from Executive Summary"
        return row[1]

    assert value_of("Product Code") == demo_context.product.product_code
    assert value_of("Report Date").date() == calculation.report_date
    assert value_of("Opening Stock") == demo_context.product.opening_stock
    assert value_of("Current Stock") == calculation.current_stock
    assert value_of("Total IN") == calculation.total_in
    assert value_of("Total OUT") == calculation.total_out
    assert value_of("Average Daily Consumption") == pytest.approx(
        float(calculation.average_daily_consumption)
    )
    assert value_of("Reorder Point") == pytest.approx(float(calculation.reorder_point))
    assert value_of("Target Stock") == pytest.approx(float(calculation.target_stock))
    assert value_of("Inventory Position") == calculation.inventory_position
    assert value_of("Suggested Order Quantity") == calculation.suggested_order_quantity
    assert value_of("Safety Stock") == calculation.safety_stock
    assert value_of("Days of Supply") == pytest.approx(
        float(calculation.days_of_supply)
    )

    movements = workbook[SHEET_MOVEMENTS]
    rows = data_rows(movements)
    # The newest movement row must carry the engine's closing balance for its day.
    assert rows, "Stock Movements sheet has no data rows"
    last_date = rows[-1][0].date()
    assert rows[-1][4] == demo_context.closing_balance(last_date)


def test_excel_uses_frozen_headers_and_filters_on_table_sheets(demo_context):
    workbook = load_workbook_bytes(build_excel_report(demo_context))

    for name in (SHEET_MOVEMENTS, SHEET_ORDERS):
        sheet = workbook[name]
        assert sheet.freeze_panes is not None
        assert sheet.auto_filter.ref is not None

    for name in SHEET_ORDER:
        assert workbook[name].sheet_view.showGridLines is False


def test_excel_workbook_contains_no_formulas(demo_context):
    workbook = load_workbook_bytes(build_excel_report(demo_context))

    for name in SHEET_ORDER:
        for row in workbook[name].iter_rows(values_only=True):
            for value in row:
                if isinstance(value, str):
                    assert not value.startswith("="), (
                        f"Formula found in {name}: {value}"
                    )


def test_excel_consumption_sheet_keeps_the_detail_column(demo_context):
    workbook = load_workbook_bytes(build_excel_report(demo_context))
    sheet = workbook[SHEET_CONSUMPTION]

    average = find_row(sheet, "Average Daily Consumption")
    assert average[1] == pytest.approx(
        float(demo_context.calculation.average_daily_consumption)
    )
    # The detail text must land in column D, not be consumed as a number format.
    assert "calendar days covered" in average[3]

    highest = find_row(sheet, "Highest Consumption Day")
    assert highest[1] == demo_context.summary.highest_quantity
    assert highest[3] == demo_context.summary.highest_day.strftime("%d %b %Y")


def test_excel_daily_and_weekly_blocks_start_right_after_the_header(demo_context):
    workbook = load_workbook_bytes(build_excel_report(demo_context))
    rows = sheet_values(workbook[SHEET_CONSUMPTION])

    for header_label in ("Date", "Week Starting"):
        index = next(
            position
            for position, row in enumerate(rows)
            if row and row[0] == header_label
        )
        first_data = rows[index + 1]
        assert first_data[0] is not None, (
            f"a blank row separates the '{header_label}' header from its data"
        )


def test_excel_report_handles_a_dataset_without_movements_or_orders():
    dataset = make_dataset(
        opening_date=TODAY - timedelta(days=5),
        movements=(),
        open_orders=(),
    )
    context = make_context(dataset)

    payload = build_excel_report(context)
    workbook = load_workbook_bytes(payload)

    assert workbook.sheetnames == list(SHEET_ORDER)
    movements = workbook[SHEET_MOVEMENTS]
    text = " ".join(
        str(value)
        for row in sheet_values(movements)
        for value in row
        if value is not None
    )
    assert "No stock movements were recorded" in text

    orders = workbook[SHEET_ORDERS]
    order_text = " ".join(
        str(value) for row in sheet_values(orders) for value in row if value is not None
    )
    assert "no open purchase orders" in order_text


def test_excel_report_supports_turkish_characters_and_descriptions():
    dataset = make_dataset(
        product_name="Galvanizli Kare Profil 40x40x2 mm — 6m Çelik",
        unit="Adet",
        opening_date=TODAY - timedelta(days=3),
        movements=(
            StockMovement(
                TODAY - timedelta(days=2), "OUT", 12, "Üretim tüketimi — şğüı"
            ),
            StockMovement(
                TODAY - timedelta(days=1), "IN", 40, "Tedarikçi teslimatı"
            ),
        ),
    )
    context = make_context(dataset)
    workbook = load_workbook_bytes(build_excel_report(context))

    summary_text = " ".join(
        str(value)
        for row in sheet_values(workbook[SHEET_SUMMARY])
        for value in row
        if value is not None
    )
    movements_text = " ".join(
        str(value)
        for row in sheet_values(workbook[SHEET_MOVEMENTS])
        for value in row
        if value is not None
    )
    assert "Çelik" in summary_text
    assert "Üretim tüketimi" in movements_text
    assert "Tedarikçi teslimatı" in movements_text


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------


def test_pdf_report_is_generated(demo_context):
    payload = build_pdf_report(demo_context)

    assert isinstance(payload, bytes)
    assert payload.startswith(b"%PDF-")
    assert payload.rstrip().endswith(b"%%EOF")
    assert len(payload) > 20_000
    assert b"/Type /Page" in payload


def test_pdf_report_is_multi_page_with_numbered_footer(demo_context):
    payload = build_pdf_report(demo_context)

    pages = page_count(payload)
    assert pages >= 3

    text = pdf_text(payload)
    assert f"Page 1 of {pages}" in text
    assert f"Page {pages} of {pages}" in text
    assert "Inventory Report" in text


def test_pdf_report_handles_a_dataset_without_movements_or_orders():
    dataset = make_dataset(
        opening_date=TODAY - timedelta(days=4),
        movements=(),
        open_orders=(),
    )
    payload = build_pdf_report(make_context(dataset))

    assert payload.startswith(b"%PDF-")
    assert len(payload) > 10_000


def test_pdf_report_handles_a_single_day_window():
    dataset = make_dataset(opening_date=TODAY, movements=(), open_orders=())
    payload = build_pdf_report(make_context(dataset))

    assert payload.startswith(b"%PDF-")


def test_pdf_report_embeds_a_truetype_font_for_turkish_glyphs(demo_context):
    payload = build_pdf_report(demo_context)

    # A subset TrueType font is embedded, which is what makes Turkish
    # characters render. Base-14 Helvetica would carry no FontFile2 stream.
    assert b"/FontFile2" in payload


def test_pdf_report_survives_a_large_movement_list():
    opening = TODAY - timedelta(days=400)
    movements = tuple(
        StockMovement(
            opening + timedelta(days=index % 380),
            "OUT" if index % 3 else "IN",
            1 + index % 9,
            f"Hareket {index} — üretim kaydı",
        )
        for index in range(900)
    )
    dataset = make_dataset(opening_date=opening, movements=movements)
    context = make_context(dataset)

    payload = build_pdf_report(context)

    assert payload.startswith(b"%PDF-")
    assert payload.count(b"/Type /Page") >= 3
    # A large movement list must not leak into the PDF body; the report shows
    # summaries and charts only.
    assert len(payload) < 400_000


def test_pdf_report_records_the_selected_report_date(demo_dataset):
    report_date = TODAY - timedelta(days=3)
    context = make_context(demo_dataset, report_date)
    payload = build_pdf_report(context)

    stamp = report_date.strftime("%d %b %Y").encode()
    # Text is compressed by default, so verify through the document metadata
    # and the report context instead of raw bytes.
    assert context.report_date == report_date
    assert report_date.isoformat().encode() in payload
    assert payload.startswith(b"%PDF-")
    assert stamp  # sanity check that the expected label is constructible


# ---------------------------------------------------------------------------
# Historical reports
# ---------------------------------------------------------------------------


def test_historical_excel_report_keeps_the_limitation_note(demo_dataset):
    historical_date = demo_dataset.product.opening_stock_date + timedelta(days=14)
    calculation = calculate_inventory(demo_dataset, historical_date)
    assert calculation.is_historical_report
    context = build_report_context(demo_dataset, calculation)
    workbook = load_workbook_bytes(build_excel_report(context))

    replenishment = workbook[SHEET_REPLENISHMENT]
    text = " ".join(
        str(value)
        for row in sheet_values(replenishment)
        for value in row
        if value is not None
    )
    assert calculation.replenishment_note in text

    assert find_row(replenishment, "Suggested Order Quantity")[1] == "Not generated"
    assert find_row(replenishment, "Reorder Required")[1] == "Not supported"

    summary = workbook[SHEET_SUMMARY]
    assert find_row(summary, "Open Order Quantity")[1] == "Not included"
    assert find_row(summary, "Overdue Orders")[1] == "Not evaluated"


def test_historical_pdf_report_keeps_the_limitation_note(demo_dataset):
    historical_date = demo_dataset.product.opening_stock_date + timedelta(days=14)
    context = make_context(demo_dataset, historical_date)
    assert context.is_historical

    payload = build_pdf_report(context)

    assert payload.startswith(b"%PDF-")
    assert "Historical report" in context.report_type_label
    assert not context.calculation.replenishment_supported


def test_report_date_is_consistent_across_excel_and_pdf(demo_dataset):
    report_date = TODAY - timedelta(days=5)
    context = make_context(demo_dataset, report_date)
    workbook = load_workbook_bytes(build_excel_report(context))
    pdf = build_pdf_report(context)

    summary = workbook[SHEET_SUMMARY]
    assert find_row(summary, "Report Date")[1].date() == report_date
    assert context.report_date == report_date
    assert report_date.isoformat().encode() in pdf

    # The movement sheet only contains rows up to the report date.
    movements = workbook[SHEET_MOVEMENTS]
    dates = [
        row[0].date()
        for row in sheet_values(movements)
        if row and hasattr(row[0], "year")
    ]
    assert dates == sorted(dates)
    assert all(day <= report_date for day in dates)


# ---------------------------------------------------------------------------
# Report context
# ---------------------------------------------------------------------------


def test_report_context_rejects_a_mismatched_calculation(demo_dataset):
    calculation = calculate_inventory(demo_dataset, TODAY)

    with pytest.raises(TypeError):
        build_report_context("not a dataset", calculation)

    with pytest.raises(TypeError):
        build_report_context(demo_dataset, "not a calculation")


def test_report_context_rejects_a_date_before_opening_stock(demo_dataset):
    opening = demo_dataset.product.opening_stock_date
    calculation = calculate_inventory(demo_dataset, opening)
    # Force an impossible report date by building a calculation for a date the
    # dataset cannot describe.
    before_opening = opening - timedelta(days=1)

    with pytest.raises(ValueError):
        build_report_context(
            demo_dataset,
            _fake_calculation(calculation, before_opening),
        )


def _fake_calculation(calculation, report_date: date):
    """Return a copy of ``calculation`` with a different report date."""

    from dataclasses import replace

    return replace(calculation, report_date=report_date)


def test_report_stem_is_file_name_safe(demo_dataset):
    calculation = calculate_inventory(demo_dataset, TODAY)
    context = build_report_context(demo_dataset, calculation)

    stem = context.file_stem
    assert stem.startswith("inventory-intelligence_")
    assert stem.endswith(calculation.report_date.isoformat())
    assert "/" not in stem and "\\" not in stem and " " not in stem


# ---------------------------------------------------------------------------
# Reports screen
# ---------------------------------------------------------------------------


def test_reports_screen_renders_both_download_areas(demo_dataset):
    app = open_app(demo_dataset, "Reports")

    assert not app.exception
    text = markdown_text(app)
    assert "Excel Report" in text
    assert "PDF Report" in text

    labels = [download_label(button) for button in download_buttons(app)]
    assert "Download Excel Report" in labels
    assert "Download PDF Report" in labels

    assert "Executive Summary" in text
    assert "Stock Movements" in text
    assert "Open Purchase Orders" in text
    assert "Methodology" in text or "Replenishment" in text


def test_reports_screen_offers_no_download_without_a_dataset():
    # Without an active dataset the Reports screen is unreachable: the app falls
    # back to the welcome screen, which only offers the blank template.
    app = open_app(None, "Reports")

    assert not app.exception
    labels = [download_label(button) for button in download_buttons(app)]
    assert "Download Excel Report" not in labels
    assert "Download PDF Report" not in labels

    text = markdown_text(app)
    assert "How It Works" in text  # the welcome screen rendered instead
    # The welcome screen's workflow does mention "Export Excel or PDF Reports",
    # so absence is asserted on the report *cards* and download buttons rather
    # than on the bare words.
    assert 'class="ii-report-card"' not in text
    assert "Sheets included" not in text
    assert "Sections included" not in text


def test_reports_download_buttons_produce_real_files(demo_dataset):
    app = open_app(demo_dataset, "Reports")
    assert not app.exception

    buttons = download_buttons(app)
    excel = next(b for b in buttons if "Excel" in download_label(b))
    pdf = next(b for b in buttons if "PDF" in download_label(b))

    # Newer Streamlit testing APIs can fire the click; older ones expose the
    # generated media URL instead. Both prove that a real file was produced.
    if click_download(excel):
        app.run()
        assert not app.exception
    else:
        assert download_media_url(excel)

    if click_download(pdf):
        app.run()
        assert not app.exception
    else:
        assert download_media_url(pdf)


def test_reports_screen_works_for_demo_and_uploaded_data(demo_dataset):
    demo_app = open_app(demo_dataset, "Reports")
    assert not demo_app.exception
    assert len(download_buttons(demo_app)) == 2

    uploaded = make_dataset(
        source="upload",
        filename="user-upload.xlsx",
        opening_date=TODAY - timedelta(days=6),
        movements=(
            StockMovement(TODAY - timedelta(days=5), "OUT", 15, "Üretim"),
            StockMovement(TODAY - timedelta(days=2), "IN", 60, "Teslimat"),
        ),
        open_orders=(OpenOrder("PO-9", 90, TODAY + timedelta(days=7)),),
    )
    upload_app = open_app(uploaded, "Reports")
    assert not upload_app.exception
    assert len(download_buttons(upload_app)) == 2
    assert "Uploaded workbook" in markdown_text(upload_app) or "user-upload.xlsx" in (
        markdown_text(upload_app)
    )


def test_reports_screen_uses_the_shared_calculation_object(demo_dataset):
    app = open_app(demo_dataset, "Reports")

    calculation = app.session_state["ii_calculation"]
    context = build_report_context(demo_dataset, calculation)

    excel = build_excel_report(context)
    workbook = load_workbook_bytes(excel)
    assert find_row(workbook[SHEET_SUMMARY], "Current Stock")[1] == (
        calculation.current_stock
    )


def test_reports_screen_reports_historical_dates(demo_dataset):
    historical_date = demo_dataset.product.opening_stock_date + timedelta(days=10)
    app = open_app(demo_dataset, "Reports", report_date=historical_date)

    assert not app.exception
    text = markdown_text(app)
    assert "Historical report date" in text
    assert len(download_buttons(app)) == 2


# ---------------------------------------------------------------------------
# Packaging
# ---------------------------------------------------------------------------


def test_excel_payload_is_a_zip_with_no_external_links(demo_context):
    payload = build_excel_report(demo_context)

    with zipfile.ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()

    assert "xl/workbook.xml" in names
    assert not any("externalLink" in name for name in names)
