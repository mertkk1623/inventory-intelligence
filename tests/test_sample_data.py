"""Tests for the generated blank template and the curated demo scenarios.

The Quick Start panel hands out three things: an empty workbook that teaches
the contract, and populated workbooks that exercise the calculation engine and
the AI layer. All three are generated from :mod:`core.schema`, so these tests
guard two properties at once: the generated files stay inside the validator
contract, and the scenarios keep producing the specific signals the UI copy
promises.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from ai.context_builder import build_ai_context
from core.calculations import calculate_inventory
from core.excel_reader import read_workbook
from core.schema import SHEET_SPECS
from core.validation import validate_excel
from utils.data_loader import load_sample_dataset
from utils.i18n import has_translation, set_language, t
from utils.sample_data import (
    BLANK_TEMPLATE_FILENAME,
    DEFAULT_SCENARIO_KEY,
    GUIDE_ROWS,
    READ_ME_SHEET,
    SAMPLE_SCENARIOS,
    SCENARIO_KEYS,
    blank_template_bytes,
    blank_template_sheets,
    cached_blank_template_bytes,
    cached_sample_workbook_bytes,
    get_scenario,
    sample_filename,
    sample_workbook_bytes,
)

APP_PATH = __import__("pathlib").Path(__file__).resolve().parents[1] / "app.py"
TODAY = date.today()


def _validate(
    payload: bytes, *, filename: str = "scenario.xlsx", source: str = "sample"
):
    return validate_excel(BytesIO(payload), filename=filename, source_kind=source)


@pytest.fixture(autouse=True)
def _restore_language():
    """Keep the translation tests from leaking into the AppTest based ones."""

    yield
    set_language("en")


# ---------------------------------------------------------------------------
# Blank template
# ---------------------------------------------------------------------------


def test_blank_template_headers_match_the_schema():
    sheets = read_workbook(blank_template_bytes())

    for spec in SHEET_SPECS:
        assert spec.name in sheets
        assert tuple(sheets[spec.name].columns) == spec.required_columns


def test_blank_template_sheets_helper_is_empty_and_typed():
    sheets = blank_template_sheets()

    assert tuple(sheets) == tuple(spec.name for spec in SHEET_SPECS)
    for spec in SHEET_SPECS:
        frame = sheets[spec.name]
        assert frame.empty
        assert list(frame.columns) == list(spec.required_columns)


def test_blank_template_ships_a_read_me_guide():
    sheets = read_workbook(blank_template_bytes())

    assert READ_ME_SHEET in sheets
    guide = sheets[READ_ME_SHEET]
    assert list(guide.columns) == ["Topic", "Guidance"]
    assert len(guide) == len(GUIDE_ROWS)
    # Every sheet and every column has to be documented, otherwise the guide
    # silently rots when the schema grows.
    documented = set(guide["Topic"])
    for spec in SHEET_SPECS:
        assert spec.name in documented
        for column in spec.required_columns:
            assert column in documented


def test_blank_template_is_rejected_only_for_the_empty_product_master():
    result = _validate(blank_template_bytes(), filename=BLANK_TEMPLATE_FILENAME)

    assert not result.is_valid
    assert [issue.code for issue in result.errors] == ["empty_product_master"]
    # The two warnings are expected on an empty workbook and must stay warnings.
    assert {issue.code for issue in result.warnings} == {
        "no_movements",
        "no_open_orders",
    }
    assert READ_ME_SHEET in result.sheets_found


def test_blank_template_has_a_transaction_type_dropdown():
    workbook = load_workbook(BytesIO(blank_template_bytes()))
    sheet = workbook["Stock Movements"]

    validations = list(sheet.data_validations.dataValidation)
    assert len(validations) == 1
    assert validations[0].type == "list"
    assert "IN" in validations[0].formula1
    assert "OUT" in validations[0].formula1


def test_blank_template_download_is_cached():
    assert cached_blank_template_bytes() is cached_blank_template_bytes()


# ---------------------------------------------------------------------------
# Scenario catalogue
# ---------------------------------------------------------------------------


def test_scenario_keys_are_unique_and_default_exists():
    assert len(SCENARIO_KEYS) == len(set(SCENARIO_KEYS))
    assert DEFAULT_SCENARIO_KEY in SCENARIO_KEYS
    assert len(SAMPLE_SCENARIOS) == 4


def test_unknown_scenario_is_a_loud_error():
    with pytest.raises(ValueError, match="Unknown sample scenario"):
        get_scenario("does-not-exist")


@pytest.mark.parametrize("scenario", SAMPLE_SCENARIOS, ids=lambda item: item.key)
def test_every_scenario_validates_and_is_marked_as_sample(scenario):
    result = _validate(
        sample_workbook_bytes(scenario.key), filename=sample_filename(scenario.key)
    )

    assert result.is_valid, [issue.message for issue in result.errors]
    assert result.errors == []
    dataset = result.dataset
    assert dataset is not None
    assert dataset.source == "sample"
    assert dataset.is_sample
    # Sample data is demo data: the dashboard badge and the sidebar both treat
    # it as synthetic, so a sample can never look like a real upload.
    assert dataset.is_demo
    assert dataset.filename == sample_filename(scenario.key)
    assert dataset.product.product_code == scenario.product_code
    assert dataset.movement_count == scenario.movement_count
    assert dataset.open_order_count == scenario.order_count
    assert dataset.movement_count >= 30


@pytest.mark.parametrize("scenario", SAMPLE_SCENARIOS, ids=lambda item: item.key)
def test_scenario_shape_does_not_depend_on_the_reference_date(scenario):
    """The scenarios are anchored to "today", so they must age cleanly.

    Movement offsets are relative to the opening date; if a scenario ever
    hard-coded a date, the engine numbers would drift as the app ages and every
    claim in the UI copy would go stale.
    """

    def signature(reference: date) -> tuple:
        result = _validate(sample_workbook_bytes(scenario.key, reference=reference))
        assert result.is_valid
        calculation = calculate_inventory(result.dataset, reference)
        return (
            calculation.current_stock,
            round(float(calculation.average_daily_consumption), 4),
            None
            if calculation.days_of_supply is None
            else round(float(calculation.days_of_supply), 4),
            int(calculation.reorder_point),
            calculation.suggested_order_quantity,
            calculation.reorder_required,
            calculation.negative_stock_warning,
            calculation.overdue_order_count,
        )

    anchors = (date.today(), date(2031, 7, 3), date(2027, 2, 28))
    signatures = {signature(anchor) for anchor in anchors}
    assert len(signatures) == 1, signatures


@pytest.mark.parametrize("scenario", SAMPLE_SCENARIOS, ids=lambda item: item.key)
def test_generated_workbook_reuploads_through_the_normal_upload_path(scenario):
    """The download button promises a file the uploader accepts again."""

    result = _validate(sample_workbook_bytes(scenario.key), source="upload")

    assert result.is_valid
    assert result.dataset is not None
    assert result.dataset.source == "upload"
    # Re-uploaded data is the user's file now, not demo data.
    assert not result.dataset.is_demo
    assert not result.dataset.is_sample


@pytest.mark.parametrize("scenario", SAMPLE_SCENARIOS, ids=lambda item: item.key)
def test_sample_download_is_cached_per_day(scenario):
    first = cached_sample_workbook_bytes(scenario.key, reference=TODAY)
    second = cached_sample_workbook_bytes(scenario.key, reference=TODAY)

    assert first is second
    # A different anchor must not be served from the same cache entry.
    other = cached_sample_workbook_bytes(scenario.key, reference=date(2031, 7, 3))
    assert other is not first


# ---------------------------------------------------------------------------
# Scenario signals: the numbers the UI copy talks about
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", SAMPLE_SCENARIOS, ids=lambda item: item.key)
def test_scenarios_are_accepted_by_the_ai_context_builder(scenario):
    result = _validate(sample_workbook_bytes(scenario.key))
    calculation = calculate_inventory(result.dataset, TODAY)

    context = build_ai_context(result.dataset, calculation)

    payload = context.payload
    assert payload["report_type"] == "current"
    assert payload["product"]["code"] == scenario.product_code
    assert payload["stock"]["current_stock"] == calculation.current_stock
    # The payload rounds money-like values to two places, so compare rounded.
    assert payload["replenishment"]["reorder_point"] == pytest.approx(
        round(float(calculation.reorder_point), 2)
    )
    assert len(payload["recent_movements"]) == scenario.movement_count
    assert len(payload["open_orders"]) == scenario.order_count
    assert context.fingerprint


def _calculation_for(key: str):
    result = _validate(sample_workbook_bytes(key))
    assert result.is_valid and result.dataset is not None
    return result.dataset, calculate_inventory(result.dataset, TODAY)


def test_stockout_scenario_reports_a_reorder_need_and_an_overdue_order():
    dataset, calculation = _calculation_for("stockout")

    assert dataset.product.safety_stock == 300
    assert calculation.current_stock == 59
    assert calculation.current_stock < calculation.safety_stock
    assert float(calculation.average_daily_consumption) == pytest.approx(16.67, abs=0.01)
    assert float(calculation.days_of_supply) == pytest.approx(3.54, abs=0.01)
    assert calculation.reorder_required
    assert calculation.suggested_order_quantity > 0
    assert calculation.overdue_order_count == 1
    assert not calculation.negative_stock_warning
    assert calculation.lowest_stock_balance == 59


def test_dead_stock_scenario_ties_up_capital_and_never_reorders():
    dataset, calculation = _calculation_for("dead_stock")

    assert calculation.current_stock == 4577
    assert calculation.average_daily_consumption < 5
    assert calculation.days_of_supply is not None
    assert float(calculation.days_of_supply) > 1000
    assert not calculation.reorder_required
    assert calculation.suggested_order_quantity == 0
    assert not calculation.negative_stock_warning
    assert dataset.open_order_count == 1


def test_negative_stock_scenario_goes_below_zero_and_recovers():
    _, calculation = _calculation_for("negative_stock")

    assert calculation.negative_stock_warning
    assert calculation.lowest_stock_balance < 0
    assert calculation.lowest_stock_balance == -306
    assert calculation.current_stock > 0
    assert float(calculation.days_of_supply) == pytest.approx(7.13, abs=0.01)


def test_fast_mover_scenario_has_healthy_cover():
    _, calculation = _calculation_for("fast_mover")

    assert calculation.current_stock == 1827
    assert float(calculation.average_daily_consumption) == pytest.approx(25.70, abs=0.01)
    assert float(calculation.days_of_supply) == pytest.approx(71.09, abs=0.01)
    assert calculation.inventory_position >= calculation.reorder_point
    assert not calculation.reorder_required
    assert not calculation.negative_stock_warning


def test_turnover_spread_makes_the_scenarios_meaningfully_different():
    """Guard the ABC-style contrast the panel copy relies on.

    V1 is single-SKU, so the four scenarios have to differ by velocity for the
    comparison to say anything at all.
    """

    supply = {}
    for scenario in SAMPLE_SCENARIOS:
        _, calculation = _calculation_for(scenario.key)
        assert calculation.days_of_supply is not None
        supply[scenario.key] = float(calculation.days_of_supply)

    assert supply["dead_stock"] > supply["fast_mover"] > supply["negative_stock"]
    assert supply["dead_stock"] > supply["stockout"]
    # Almost three orders of magnitude between the extremes.
    assert supply["dead_stock"] / supply["stockout"] > 100


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def test_load_sample_dataset_activates_the_state():
    result = load_sample_dataset(DEFAULT_SCENARIO_KEY)

    assert result.is_valid
    assert result.dataset is not None
    assert result.dataset.is_sample
    assert result.dataset.product.product_code == get_scenario(
        DEFAULT_SCENARIO_KEY
    ).product_code
    assert result.dataset.filename == sample_filename(DEFAULT_SCENARIO_KEY)


def test_load_sample_dataset_rejects_an_unknown_scenario():
    with pytest.raises(ValueError):
        load_sample_dataset("nope")


# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

_QUICK_START_KEYS = (
    "Quick Start & Demo Data",
    "Try the app and the AI without preparing a file",
    "Run the AI demo",
    "Demo scenario",
    "🚀 Run the AI demo now",
    "Blank data template",
    "📥 Download blank template",
    "Populated sample file",
    "File to download",
    "📊 Download sample data",
    "Each scenario is built to trigger a different set of warnings.",
    "The blank template could not be generated.",
    "The sample workbook could not be generated.",
)


def test_quick_start_panel_is_fully_translated():
    missing = [key for key in _QUICK_START_KEYS if not has_translation(key)]
    assert missing == []


def test_every_scenario_name_and_summary_is_translated():
    missing = [
        text
        for scenario in SAMPLE_SCENARIOS
        for text in (scenario.name, scenario.summary)
        if not has_translation(text)
    ]
    assert missing == []


def test_turkish_labels_differ_from_english():
    set_language("tr")

    assert t("Quick Start & Demo Data") == "Hızlı Başlangıç ve Örnek Veri"
    assert t("Stockout risk") != "Stockout risk"
    assert t("📊 Download sample data").startswith("📊")


# ---------------------------------------------------------------------------
# Streamlit wiring
# ---------------------------------------------------------------------------


def test_welcome_screen_renders_the_quick_start_panel():
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()

    assert not app.exception

    markdown = "\n".join(str(element.value) for element in app.markdown)
    # Section headers are HTML-escaped, so the ampersand appears encoded.
    assert "Quick Start &amp; Demo Data" in markdown

    labels = [button.label for button in app.button]
    assert "🚀 Run the AI demo now" in labels
    assert "Load Demo Data" in labels

    downloads = [widget.label for widget in app.get("download_button")]
    assert "📥 Download blank template" in downloads
    assert "📊 Download sample data" in downloads

    # The upload area is untouched by the new panel.
    assert len(app.get("file_uploader")) == 1


def test_quick_start_scenario_cards_describe_each_scenario():
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()

    markdown = "\n".join(str(element.value) for element in app.markdown)
    for scenario in SAMPLE_SCENARIOS:
        assert scenario.product_code in markdown
        assert scenario.name in markdown

    assert markdown.count('class="ii-scenario-card"') == len(SAMPLE_SCENARIOS)


def test_quick_start_button_loads_the_selected_scenario_and_opens_the_dashboard():
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.selectbox(key="ii_sample_scenario_widget").set_value("Dead stock").run()
    app.button(key="load_sample_demo").click().run()

    assert not app.exception

    dataset = app.session_state["ii_dataset"]
    assert dataset.is_sample
    assert dataset.product.product_code == get_scenario("dead_stock").product_code
    assert app.session_state["ii_page"] == "Dashboard"

    markdown = "\n".join(str(element.value) for element in app.markdown)
    assert "Demo data" in markdown


def test_quick_start_panel_renders_in_turkish():
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.selectbox(key="ii_language_widget").set_value("Türkçe").run()

    assert not app.exception

    markdown = "\n".join(str(element.value) for element in app.markdown)
    assert "Hızlı Başlangıç ve Örnek Veri" in markdown
    assert "Stok tükenme riski" in markdown

    labels = [button.label for button in app.button]
    assert "🚀 AI demosunu hemen çalıştır" in labels


def test_demo_and_sample_sources_stay_separate():
    """The bundled demo and the generated sample must not be confused."""

    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.button(key="load_demo").click().run()
    demo = app.session_state["ii_dataset"]
    assert demo.is_demo and not demo.is_sample

    # Loading the demo navigates away from the welcome screen, so the panel has
    # to be reached again before the sample button exists.
    app.radio(key="ii_nav_widget").set_value("Getting Started").run()
    app.selectbox(key="ii_sample_scenario_widget").set_value("Fast mover").run()
    app.button(key="load_sample_demo").click().run()
    sample = app.session_state["ii_dataset"]
    assert sample.is_sample and sample.is_demo
    assert sample.product.product_code != demo.product.product_code
