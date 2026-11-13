from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "Home.py")


def app(stage=None):
    at = AppTest.from_file(APP, default_timeout=30)
    if stage:
        at.session_state["stage"] = stage
    return at.run()


def test_landing_page_has_no_sidebar():
    at = app()
    assert not at.exception
    assert at.session_state["stage"] == "landing"
    assert any("Find where your data centre wastes energy" in m.value for m in at.markdown)
    assert len(at.sidebar.button) == 0


@pytest.mark.parametrize("stage, title", [
    ("upload", "Upload your data"),
    ("questions", "About your site"),
    ("analysing", "Analysing your data"),
])
def test_steps_have_no_sidebar(stage, title):
    at = app(stage)
    assert not at.exception
    assert at.title[0].value == title
    assert len(at.sidebar.button) == 0


def test_flow_from_landing_to_analysis():
    at = app()
    at.button(key="upload_top").click().run()
    assert at.session_state["stage"] == "upload"
    # The upload step itself is tested in test_upload_screen.py; continue from questions.
    at.session_state["stage"] = "questions"
    at.run()
    for expected in ("analysing", "analysis"):
        at.button(key="next").click().run()
        assert at.session_state["stage"] == expected
    assert not at.exception


def test_analysis_shows_sidebar_with_exit():
    at = app("analysis")
    assert not at.exception
    assert at.title[0].value == "Data"
    keys = [b.key for b in at.sidebar.button]
    assert "exit" in keys and "change_answers" in keys


def test_analysis_pages_in_order_and_no_home():
    from app.Home import ANALYSIS_PAGES, HERE

    titles = [t for _, t, _ in ANALYSIS_PAGES]
    assert titles == ["Data", "Energy & Cost", "Efficiency & Load", "Cooling & Weather",
                      "Anomalies", "Forecast & Planning", "How to reduce your cost",
                      "Savings calculator", "Benchmark", "Export", "Replay"]
    assert "Home" not in titles
    for file, _, _ in ANALYSIS_PAGES:
        assert (HERE / "pages" / file).exists()


def test_every_analysis_page_loads():
    from app.Home import ANALYSIS_PAGES, HERE

    at = app("analysis")
    for file, title, _ in ANALYSIS_PAGES:
        at.switch_page(str(HERE / "pages" / file)).run()
        assert not at.exception, file
        assert at.title[0].value == title


def test_exit_deletes_data_and_returns_to_landing():
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["stage"] = "analysis"
    at.session_state["file_name"] = "my_site.csv"
    at.session_state["answers"] = {"country": "India"}
    at.run()
    at.sidebar.button(key="exit").click().run()
    assert at.session_state["stage"] == "landing"
    assert at.session_state["file_name"] is None
    assert at.session_state["answers"] == {}


def test_cancel_returns_to_landing():
    at = app("questions")
    at.button(key="cancel").click().run()
    assert at.session_state["stage"] == "landing"
