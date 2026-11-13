"""Smoke tests for the Streamlit welcome screen and demo flow."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_app_starts_and_renders_welcome_screen():
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()

    assert not app.exception
    markdown = "\n".join(str(element.value) for element in app.markdown)
    assert "How It Works" in markdown
    assert "Download Excel Template" in markdown
    assert "Excel Data Requirements" in markdown
    assert len(app.get("file_uploader")) == 1
    assert len(app.button) >= 1


def test_demo_button_activates_demo_dataset():
    app = AppTest.from_file(APP_PATH, default_timeout=30).run()
    app.button(key="load_demo").click().run()

    assert not app.exception
    dataset = app.session_state["ii_dataset"]
    assert dataset.is_demo
    assert dataset.product.product_code == "PRF-4040-02"

    markdown = "\n".join(str(element.value) for element in app.markdown)
    assert "Data Overview" in markdown
