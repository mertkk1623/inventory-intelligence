"""Tests for the bilingual layer: switching, formatting and navigation safety."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from config import DEMO_FILE, DEMO_SOURCE
from core.validation import validate_excel_file
from utils.i18n import (
    LANGUAGE_WIDGET_KEY,
    format_date,
    format_days,
    format_decimal,
    format_number,
    format_quantity,
    get_language,
    resolve_language,
    set_language,
    table_date_format,
)

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"

WELCOME_EN = "Getting Started"

PAGE_PAIRS = (
    ("Dashboard", "Panel"),
    ("Stock Analysis", "Stok Analizi"),
    ("Consumption Analysis", "Tüketim Analizi"),
    ("Replenishment Planning", "İkmal Planlaması"),
    ("Reports", "Raporlar"),
    ("AI Analyst", "AI Analisti"),
)


@pytest.fixture
def demo_dataset():
    result = validate_excel_file(DEMO_FILE, source_kind=DEMO_SOURCE)
    assert result.is_valid
    return result.dataset


def _tree_language(app: AppTest) -> str:
    """Language the currently rendered element tree was produced in.

    ``AppTest`` replays widget state by re-invoking ``format_func`` outside a
    script run, where ``utils.i18n.t()`` deliberately falls back to the English
    module default. The fallback therefore has to match the tree being replayed.
    """

    try:
        options = list(app.radio[0].options)
    except (KeyError, IndexError):
        return "en"
    return "en" if not options or options[0] == WELCOME_EN else "tr"


def _run(app: AppTest) -> AppTest:
    set_language(_tree_language(app))
    return app.run()


def _open_on(page: str, dataset) -> AppTest:
    """Open the app directly on ``page`` with the demo dataset active."""

    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.session_state["ii_dataset"] = dataset
    app.session_state["ii_page"] = page
    app.session_state["ii_pending_page"] = page
    _run(app)
    return app


def _switch_language(app: AppTest, label: str) -> AppTest:
    """Pick a language the way the sidebar selectbox does.

    The widget is addressed by key: the welcome screen also renders scenario
    selectboxes, so a positional index would be fragile.
    """

    app.selectbox(key=LANGUAGE_WIDGET_KEY).set_value(label)
    _run(app)
    return app


def _markdown(app: AppTest) -> str:
    return "\n".join(str(element.value) for element in app.markdown)


# ---------------------------------------------------------------------------
# Language resolution
# ---------------------------------------------------------------------------


def test_resolve_language_accepts_supported_codes_only():
    assert resolve_language("tr") == "tr"
    assert resolve_language("en") == "en"
    assert resolve_language("de") == "en"
    assert resolve_language(None) == "en"
    assert resolve_language(42) == "en"


def test_set_language_returns_the_resolved_code():
    assert set_language("tr") == "tr"
    assert get_language() == "tr"
    assert set_language("nonsense") == "en"
    assert get_language() == "en"


def test_translation_table_has_no_duplicate_keys():
    source = (Path(__file__).resolve().parents[1] / "utils" / "i18n.py").read_text(
        encoding="utf-8"
    )
    # A duplicate key would silently override an earlier translation, so the
    # raw source is checked rather than the resulting dict.
    import ast

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and len(node.keys) > 100:
            keys = [
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            ]
            assert len(keys) == len(set(keys)), "duplicate translation key"
            assert len(keys) > 400
            return
    pytest.fail("translation table not found")


# ---------------------------------------------------------------------------
# Locale formatting: display only
# ---------------------------------------------------------------------------


def test_english_formatting_uses_dots_and_english_dates():
    set_language("en")
    assert format_number(1234.5, places=1) == "1,234.5"
    assert format_decimal(9.3667, places=2) == "9.37"
    assert format_days(47.94) == "47.9 days"
    assert format_date(date(2026, 11, 13)) == "13 Nov 2026"
    assert table_date_format() == "YYYY-MM-DD"


def test_turkish_formatting_uses_commas_and_turkish_dates():
    set_language("tr")
    assert format_number(1234.5, places=1) == "1.234,5"
    assert format_decimal(9.3667, places=2) == "9,37"
    assert format_days(47.94) == "47,9 gün"
    assert format_date(date(2026, 11, 13)) == "13.11.2026"
    assert table_date_format() == "DD.MM.YYYY"


def test_formatting_never_changes_the_underlying_value():
    set_language("tr")
    value = 449
    assert format_quantity(value, "Adet") == "449 Adet"
    assert value == 449
    assert format_number(449) == "449"


def test_missing_days_of_supply_renders_an_em_dash_in_both_languages():
    for code in ("en", "tr"):
        set_language(code)
        assert format_days(None) == "—"


# ---------------------------------------------------------------------------
# Navigation safety
# ---------------------------------------------------------------------------


def test_language_switch_keeps_the_active_screen(demo_dataset):
    for english, turkish in PAGE_PAIRS:
        app = _open_on(english, demo_dataset)
        assert app.session_state["ii_page"] == english

        _switch_language(app, "Türkçe")

        assert not list(app.exception)
        assert app.session_state["ii_language"] == "tr"
        assert app.session_state["ii_page"] == english, (
            f"switching to Turkish moved the user off {english}"
        )
        assert turkish in _markdown(app)

        _switch_language(app, "English")
        assert not list(app.exception)
        assert app.session_state["ii_language"] == "en"
        assert app.session_state["ii_page"] == english


def test_language_switch_from_the_welcome_screen_stays_on_welcome():
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    assert app.session_state["ii_page"] == WELCOME_EN

    _switch_language(app, "Türkçe")

    assert not list(app.exception)
    assert app.session_state["ii_page"] == WELCOME_EN
    assert "Başlangıç" in list(app.radio[0].options)


def test_language_survives_navigation(demo_dataset):
    app = _open_on("Dashboard", demo_dataset)
    _switch_language(app, "Türkçe")

    app.radio[0].set_value("Raporlar")
    _run(app)

    assert not list(app.exception)
    assert app.session_state["ii_language"] == "tr"
    assert app.session_state["ii_page"] == "Reports"


def test_report_date_survives_a_language_switch(demo_dataset):
    app = _open_on("Dashboard", demo_dataset)
    app.date_input[0].set_value(date(2026, 10, 20))
    app.run()
    chosen = app.session_state["ii_report_date"]

    _switch_language(app, "Türkçe")

    assert app.session_state["ii_report_date"] == chosen
    assert app.date_input[0].value == chosen


def test_all_screens_render_in_both_languages(demo_dataset):
    for english, turkish in PAGE_PAIRS:
        for label, expected in (("English", english), ("Türkçe", turkish)):
            app = _open_on(english, demo_dataset)
            _switch_language(app, label)

            run_exceptions = list(app.exception)
            assert not run_exceptions, f"{english}/{label}: {run_exceptions}"
            assert expected in _markdown(app), f"{english}/{label}: title missing"


# ---------------------------------------------------------------------------
# Document language: locale-aware CSS upper-casing
# ---------------------------------------------------------------------------


def test_document_language_is_synced_to_the_active_language():
    """The app must tell the browser which language the text is in.

    Eyebrows, badges and KPI labels are upper-cased with CSS. CSS upper-casing
    follows the element language, and Streamlit hard-codes ``lang="en"``, which
    turned Turkish ``Örnek Veri`` into ``ÖRNEK VERI`` instead of ``ÖRNEK VERİ``.
    The fix sets ``<html lang>`` from a script-only iframe, so the assertion here
    is that the helper is emitted and carries the active language.
    """

    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    assert not app.exception

    english_frames = [element.proto.srcdoc for element in app.get("iframe")]
    assert any("documentElement" in frame for frame in english_frames)
    assert any('setAttribute("lang", "en")' in frame for frame in english_frames)

    _switch_language(app, "Türkçe")

    assert not app.exception
    turkish_frames = [element.proto.srcdoc for element in app.get("iframe")]
    assert any('setAttribute("lang", "tr")' in frame for frame in turkish_frames)
    assert not any('setAttribute("lang", "en")' in frame for frame in turkish_frames)


def test_language_sync_never_breaks_the_welcome_screen():
    """The helper is a side effect; it must not raise or hide the UI."""

    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    _switch_language(app, "Türkçe")

    assert not list(app.exception)
    assert "Hızlı Başlangıç ve Örnek Veri" in _markdown(app)
