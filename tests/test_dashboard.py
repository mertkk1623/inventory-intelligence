"""Package 3 tests: analytics series and Streamlit dashboard integration."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from analytics.series import (
    consumption_summary,
    daily_consumption_series,
    filter_movements,
    movement_totals,
    open_order_rows,
    stock_balance_series,
    stock_status_label,
    weekly_consumption_series,
)
from config import DEMO_FILE, DEMO_SOURCE
from core.calculations import calculate_inventory
from core.models import (
    InventoryDataset,
    OpenOrder,
    ProductMaster,
    StockMovement,
)
from core.validation import validate_excel_file
from utils.data_loader import load_demo_dataset, load_uploaded_dataset

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
TODAY = date.today()


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def make_dataset(
    *,
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
        product_code="PRF-4040-02",
        product_name="Galvanised Square Profile 40x40",
        unit="Adet",
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


def open_app(
    dataset: InventoryDataset | None = None,
    page: str | None = None,
    *,
    report_date: date | None = None,
) -> AppTest:
    """Run the app with a pre-activated dataset and optional page."""

    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
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


def chart_count(app: AppTest) -> int:
    return len(app.get("plotly_chart"))


def _proto_date(value: str) -> date:
    """Parse the date string a Streamlit widget proto exposes.

    Streamlit serialises widget dates as ``YYYY-MM-DD`` on some versions and
    ``YYYY/MM/DD`` on others, so both separators are accepted.
    """

    year, month, day = (int(part) for part in value.replace("/", "-").split("-"))
    return date(year, month, day)


def dataframe_text(app: AppTest) -> str:
    """Flatten every rendered dataframe into searchable text."""

    chunks: list[str] = []
    for element in app.dataframe:
        value = element.value
        chunks.append(value.to_string())
        chunks.extend(str(column) for column in value.columns)
        chunks.extend(value.astype(str).to_numpy().ravel().tolist())
    return "\n".join(chunks)


def kpi_value(app: AppTest, label: str) -> str:
    """Read a KPI value from the rendered metric cards."""

    text = markdown_text(app)
    marker = f'<div class="ii-metric-label">{label}</div>'
    start = text.find(marker)
    assert start != -1, f"KPI card '{label}' was not rendered"
    value_start = text.find('<div class="ii-metric-value">', start)
    value_end = text.find("</div>", value_start)
    return text[value_start + len('<div class="ii-metric-value">') : value_end]


# ---------------------------------------------------------------------------
# Series derivations
# ---------------------------------------------------------------------------


def test_stock_balance_series_matches_engine_balance():
    dataset = make_dataset(
        opening_stock=100,
        opening_date=TODAY - timedelta(days=4),
        movements=(
            StockMovement(TODAY - timedelta(days=3), "OUT", 20),
            StockMovement(TODAY - timedelta(days=1), "IN", 50),
        ),
    )

    points = stock_balance_series(dataset, TODAY)

    assert len(points) == 5
    assert points[0] == (TODAY - timedelta(days=4), 100)
    assert points[1] == (TODAY - timedelta(days=3), 80)
    assert points[3] == (TODAY - timedelta(days=1), 130)
    assert points[-1][1] == calculate_inventory(dataset, TODAY).current_stock


def test_stock_balance_series_excludes_movements_after_report_date():
    dataset = make_dataset(
        opening_stock=100,
        opening_date=TODAY - timedelta(days=3),
        movements=(
            StockMovement(TODAY - timedelta(days=2), "OUT", 10),
            StockMovement(TODAY, "IN", 900),
        ),
    )

    points = stock_balance_series(dataset, TODAY - timedelta(days=1))

    assert points[-1] == (TODAY - timedelta(days=1), 90)
    assert all(balance <= 100 for _, balance in points)


def test_stock_balance_series_rejects_report_before_opening_date():
    dataset = make_dataset(opening_date=TODAY)

    with pytest.raises(ValueError):
        stock_balance_series(dataset, TODAY - timedelta(days=1))


def test_daily_consumption_series_fills_zero_days():
    dataset = make_dataset(
        opening_stock=500,
        opening_date=TODAY - timedelta(days=9),
        movements=(
            StockMovement(TODAY - timedelta(days=8), "OUT", 15),
            StockMovement(TODAY - timedelta(days=2), "OUT", 25),
            StockMovement(TODAY - timedelta(days=1), "IN", 40),
        ),
    )

    daily = daily_consumption_series(dataset, TODAY)

    assert len(daily) == 10
    assert daily[0].day == TODAY - timedelta(days=9)
    assert daily[-1].day == TODAY
    assert sum(entry.quantity for entry in daily) == 40
    assert sum(1 for entry in daily if entry.quantity == 0) == 8
    assert [entry.quantity for entry in daily if entry.quantity] == [15, 25]


def test_weekly_consumption_aggregates_without_gaps():
    daily = daily_consumption_series(
        make_dataset(
            opening_stock=500,
            opening_date=TODAY - timedelta(days=15),
            movements=(
                StockMovement(TODAY - timedelta(days=14), "OUT", 10),
                StockMovement(TODAY - timedelta(days=10), "OUT", 5),
                StockMovement(TODAY, "OUT", 7),
            ),
        ),
        TODAY,
    )

    weekly = weekly_consumption_series(daily)

    assert sum(entry.quantity for entry in weekly) == 22
    assert weekly == tuple(sorted(weekly, key=lambda entry: entry.week_start))
    for entry in weekly:
        assert entry.week_start.weekday() == 0


def test_consumption_summary_includes_zero_days_in_lowest():
    daily = daily_consumption_series(
        make_dataset(
            opening_stock=500,
            opening_date=TODAY - timedelta(days=4),
            movements=(
                StockMovement(TODAY - timedelta(days=3), "OUT", 12),
                StockMovement(TODAY - timedelta(days=1), "OUT", 30),
            ),
        ),
        TODAY,
    )

    summary = consumption_summary(daily)

    assert summary.total == 42
    assert summary.highest_quantity == 30
    assert summary.highest_day == TODAY - timedelta(days=1)
    assert summary.lowest_quantity == 0


def test_movement_filters_and_totals():
    dataset = make_dataset(
        opening_stock=100,
        opening_date=TODAY - timedelta(days=10),
        movements=(
            StockMovement(TODAY - timedelta(days=8), "IN", 40),
            StockMovement(TODAY - timedelta(days=5), "OUT", 10),
            StockMovement(TODAY - timedelta(days=2), "OUT", 15),
        ),
    )

    out_only = filter_movements(
        dataset, TODAY - timedelta(days=9), TODAY, ("OUT",)
    )

    assert [movement.quantity for movement in out_only] == [15, 10]
    assert movement_totals(out_only) == (0, 25)

    all_movements = filter_movements(dataset, TODAY - timedelta(days=9), TODAY)
    assert movement_totals(all_movements) == (40, 25)

    narrow = filter_movements(
        dataset,
        TODAY - timedelta(days=6),
        TODAY - timedelta(days=4),
    )
    assert [movement.quantity for movement in narrow] == [10]


def test_open_order_rows_flag_overdue_orders():
    dataset = make_dataset(
        open_orders=(
            OpenOrder("PO-002", 100, TODAY + timedelta(days=5)),
            OpenOrder("PO-001", 200, TODAY - timedelta(days=1)),
        )
    )

    rows = open_order_rows(dataset, TODAY)

    assert [row.order.order_no for row in rows] == ["PO-001", "PO-002"]
    assert rows[0].is_overdue is True
    assert rows[1].is_overdue is False


def test_stock_status_labels():
    negative = calculate_inventory(
        make_dataset(
            opening_stock=10,
            movements=(StockMovement(TODAY, "OUT", 25),),
        ),
        TODAY,
    )
    reorder = calculate_inventory(make_dataset(opening_stock=0), TODAY)
    healthy = calculate_inventory(make_dataset(opening_stock=1000), TODAY)

    assert stock_status_label(negative) == "Negative stock"
    assert stock_status_label(reorder) == "Reorder required"
    assert stock_status_label(healthy) == "Healthy"


# ---------------------------------------------------------------------------
# Dashboard with real data
# ---------------------------------------------------------------------------


def test_dashboard_renders_real_calculation_values(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")

    assert not app.exception
    calculation = app.session_state["ii_calculation"]
    assert calculation.current_stock == 449
    assert calculation.total_in == 325
    assert calculation.total_out == 376

    assert kpi_value(app, "Current Stock") == "449 Adet"
    assert kpi_value(app, "Average Daily Consumption") == (
        f"{float(calculation.average_daily_consumption):,.2f} Adet/day"
    )
    assert kpi_value(app, "Days of Supply") == (
        f"{float(calculation.days_of_supply):,.1f} days"
    )
    assert kpi_value(app, "Suggested Order Quantity") == "0 Adet"

    text = markdown_text(app)
    assert "Overview Dashboard" in text
    assert "Stock Level Trend" in text
    assert "Daily Consumption Trend" in text
    assert "Safety Stock vs Reorder Point" in text
    assert "Stock Status" in text
    assert "Open Purchase Orders" in text
    tables = dataframe_text(app)
    assert "PO-2026-001" in tables
    assert "PO-2026-002" in tables
    assert chart_count(app) == 3
    assert len(app.dataframe) == 2


def test_dashboard_uses_single_shared_calculation(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")

    first = app.session_state["ii_calculation"]
    app.radio[0].set_value("Stock Analysis").run()
    second = app.session_state["ii_calculation"]

    assert not app.exception
    assert first is second


def test_every_analytics_screen_renders_without_error(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")

    for page in (
        "Dashboard",
        "Stock Analysis",
        "Consumption Analysis",
        "Replenishment Planning",
    ):
        app.radio[0].set_value(page).run()
        assert not app.exception, f"{page} raised: {app.exception}"
        assert page in markdown_text(app)

    app.radio[0].set_value("Stock Analysis").run()
    assert chart_count(app) == 1
    app.radio[0].set_value("Consumption Analysis").run()
    assert chart_count(app) == 2


# ---------------------------------------------------------------------------
# Report date behaviour
# ---------------------------------------------------------------------------


def test_report_date_defaults_to_today_and_respects_bounds(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")

    opening = demo_dataset.product.opening_stock_date
    expected = max(opening, TODAY)

    report_input = app.date_input[0]
    assert report_input.label == "Report date"
    assert report_input.value == expected
    assert _proto_date(report_input.proto.min) == opening
    assert _proto_date(report_input.proto.max) == expected
    assert app.session_state["ii_report_date"] == expected


def test_report_date_cannot_exceed_today(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")

    # A value outside the allowed range is clamped by the shared state layer
    # even if it reaches session state from an older run.
    app.session_state["ii_report_date"] = TODAY + timedelta(days=30)
    app.run()

    assert not app.exception
    assert app.date_input[0].value == max(
        demo_dataset.product.opening_stock_date, TODAY
    )
    assert app.session_state["ii_calculation"].report_date == max(
        demo_dataset.product.opening_stock_date, TODAY
    )


def test_changing_report_date_recalculates_every_screen(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")
    earlier = demo_dataset.product.opening_stock_date + timedelta(days=14)
    assert earlier < TODAY

    app.date_input[0].set_value(earlier).run()

    assert not app.exception
    calculation = app.session_state["ii_calculation"]
    assert calculation.report_date == earlier
    assert calculation.current_stock == 477
    assert calculation.is_historical_report is True
    assert kpi_value(app, "Current Stock") == "477 Adet"
    assert "Historical report" in markdown_text(app)

    app.radio[0].set_value("Replenishment Planning").run()
    text = markdown_text(app)
    assert "Historical report limitation" in text
    assert "Not supported" in text
    assert kpi_value(app, "Suggested Order Quantity") == "—"
    assert app.session_state["ii_calculation"].report_date == earlier


def test_report_date_below_opening_date_is_rejected_by_engine(demo_dataset):
    opening = demo_dataset.product.opening_stock_date
    with pytest.raises(ValueError):
        calculate_inventory(demo_dataset, opening - timedelta(days=1))


# ---------------------------------------------------------------------------
# Demo and upload integration
# ---------------------------------------------------------------------------


def test_demo_button_loads_dataset_and_dashboard():
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.button(key="load_demo").click().run()

    assert not app.exception
    dataset = app.session_state["ii_dataset"]
    assert dataset.is_demo
    assert app.session_state["ii_page"] == "Dashboard"
    assert app.session_state["ii_report_date"] == TODAY
    assert app.session_state["ii_calculation"].current_stock == 449
    assert "Overview Dashboard" in markdown_text(app)


class _StubUpload:
    """Minimal stand-in for ``streamlit.runtime.uploaded_file_manager``."""

    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self._payload = payload
        self.type = (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    def getvalue(self) -> bytes:
        return self._payload


def test_uploaded_workbook_uses_same_engine():
    payload = DEMO_FILE.read_bytes()
    validation = load_uploaded_dataset(_StubUpload("my-workbook.xlsx", payload))

    assert validation.is_valid
    assert validation.dataset is not None
    assert validation.dataset.source == "upload"

    app = open_app(validation.dataset, "Dashboard")

    assert not app.exception
    assert app.session_state["ii_dataset"].filename == "my-workbook.xlsx"
    assert app.session_state["ii_calculation"].current_stock == 449
    assert "Uploaded file" in markdown_text(app)


def test_invalid_upload_does_not_replace_active_dataset(demo_dataset):
    app = open_app(demo_dataset, "Dashboard")

    validation = load_uploaded_dataset(_StubUpload("broken.xlsx", b"not a workbook"))

    assert not validation.is_valid
    assert validation.dataset is None
    assert not app.exception
    assert app.session_state["ii_dataset"] is demo_dataset
    assert "Overview Dashboard" in markdown_text(app)


def test_demo_loader_activates_dataset(mocker=None):
    result = load_demo_dataset()

    assert result.is_valid
    assert result.dataset is not None
    assert result.dataset.is_demo


# ---------------------------------------------------------------------------
# Replenishment warnings
# ---------------------------------------------------------------------------


def test_replenishment_warns_when_reorder_required():
    dataset = make_dataset(
        opening_stock=50,
        opening_date=TODAY,
        safety_stock=100,
        movements=(),
        open_orders=(OpenOrder("PO-900", 20, TODAY + timedelta(days=3)),),
    )

    app = open_app(dataset, "Replenishment Planning")
    assert not app.exception

    calculation = app.session_state["ii_calculation"]
    assert calculation.reorder_required is True
    assert calculation.suggested_order_quantity == 30
    assert calculation.inventory_position == 70

    text = markdown_text(app)
    assert "Reorder required" in text
    assert "Inventory Position works" in text
    assert kpi_value(app, "Reorder Required") == "Yes"
    assert kpi_value(app, "Inventory Position") == "70 Adet"
    assert kpi_value(app, "Suggested Order Quantity") == "30 Adet"
    assert kpi_value(app, "Open Order Quantity") == "20 Adet"
    assert "PO-900" in dataframe_text(app)


def test_replenishment_reports_no_reorder_when_position_is_above_point(demo_dataset):
    app = open_app(demo_dataset, "Replenishment Planning")

    assert not app.exception
    calculation = app.session_state["ii_calculation"]
    assert calculation.reorder_required is False

    text = markdown_text(app)
    assert "No reorder required" in text
    assert kpi_value(app, "Reorder Required") == "No"
    assert kpi_value(app, "Overdue Orders") == "0"
    assert kpi_value(app, "Inventory Position") == "749 Adet"


def test_overdue_orders_are_counted_and_shown():
    dataset = make_dataset(
        opening_stock=1000,
        opening_date=TODAY,
        open_orders=(
            OpenOrder("PO-LATE", 100, TODAY - timedelta(days=2)),
            OpenOrder("PO-OK", 50, TODAY + timedelta(days=4)),
        ),
    )

    app = open_app(dataset, "Replenishment Planning")
    assert not app.exception

    calculation = app.session_state["ii_calculation"]
    assert calculation.overdue_order_count == 1
    assert kpi_value(app, "Overdue Orders") == "1"
    tables = dataframe_text(app)
    assert "PO-LATE" in tables
    assert "Overdue" in tables


# ---------------------------------------------------------------------------
# Empty and zero-consumption data
# ---------------------------------------------------------------------------


def test_dashboard_handles_dataset_without_movements():
    dataset = make_dataset(opening_stock=500, opening_date=TODAY)

    app = open_app(dataset, "Dashboard")

    assert not app.exception
    assert kpi_value(app, "Current Stock") == "500 Adet"
    assert kpi_value(app, "Average Daily Consumption") == "0.00 Adet/day"
    assert kpi_value(app, "Days of Supply") == "—"
    assert chart_count(app) == 3
    assert "No open purchase orders" in markdown_text(app)


def test_zero_consumption_screen_shows_zeros():
    dataset = make_dataset(
        opening_stock=200,
        opening_date=TODAY - timedelta(days=4),
        movements=(StockMovement(TODAY - timedelta(days=2), "IN", 25),),
    )

    app = open_app(dataset, "Consumption Analysis")
    assert not app.exception

    text = markdown_text(app)
    assert "No consumption recorded" in text
    assert kpi_value(app, "Average Daily Consumption") == "0.00 Adet/day"
    assert kpi_value(app, "Total Consumption") == "0 Adet"
    assert kpi_value(app, "Highest Consumption Day") == "No consumption"
    assert kpi_value(app, "Lowest Consumption Day") == "0 Adet"
    assert chart_count(app) == 2


def test_stock_analysis_shows_movement_table_first(demo_dataset):
    app = open_app(demo_dataset, "Stock Analysis")

    assert not app.exception
    text = markdown_text(app)
    assert text.index("Stock Movement History") < text.index("Stock Balance Trend")
    assert kpi_value(app, "Opening Stock") == "500 Adet"
    assert kpi_value(app, "Total IN") == "325 Adet"
    assert kpi_value(app, "Total OUT") == "376 Adet"
    assert len(app.dataframe) == 1
    assert len(app.multiselect) == 1
    assert len(app.date_input) == 3  # sidebar report date + From + To


def test_stock_analysis_transaction_type_filter(demo_dataset):
    app = open_app(demo_dataset, "Stock Analysis")

    app.multiselect[0].set_value(["OUT"]).run()

    assert not app.exception
    table = app.dataframe[0].value
    assert set(table["Transaction Type"]) == {"OUT"}
    assert len(table) == sum(
        1 for movement in demo_dataset.movements
        if movement.transaction_type == "OUT"
    )


def test_every_screen_handles_empty_dataset():
    dataset = make_dataset(opening_stock=0, opening_date=TODAY, safety_stock=0)

    app = open_app(dataset, "Dashboard")
    assert not app.exception

    for page in (
        "Dashboard",
        "Stock Analysis",
        "Consumption Analysis",
        "Replenishment Planning",
    ):
        app.radio[0].set_value(page).run()
        assert not app.exception, f"{page} raised: {app.exception}"

    app.radio[0].set_value("Stock Analysis").run()
    assert "No movements match these filters" in markdown_text(app)

    app.radio[0].set_value("Replenishment Planning").run()
    text = markdown_text(app)
    assert "No open purchase orders" in text
    assert "Inventory Position therefore equals Current Stock." in text


def test_missing_dataset_returns_to_welcome():
    app = open_app(None, "Dashboard")

    assert not app.exception
    assert app.radio[0].value == "Getting Started"
    text = markdown_text(app)
    assert "How It Works" in text
    assert "Overview Dashboard" not in text
    assert len(app.get("file_uploader")) == 1
