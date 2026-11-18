"""Shared test helpers: run the analysis once on the development data and open pages."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "Home.py")
PAGES = Path(__file__).resolve().parent.parent / "app" / "pages"
ANSWERS = {"country": "India", "city": "Pune", "price": 8.0, "currency": "INR",
           "site_type": "hpc", "cooling_system": "water_chillers", "free_cooling": "no",
           "supply_temp_c": 22.0, "vfd": "some", "ups_mode": "double_conversion",
           "unused_servers": "sometimes", "can_change": "small"}


def analyse(df, answers=None):
    """Run the full analysis like the Analysing screen does; returns (table, results)."""
    from app.pipeline import run_analysis

    answers = dict(answers or ANSWERS)
    results = run_analysis(df, answers, {}, "dev.csv")
    table = results.pop("table")
    answers["emission_factor"] = results["location"].get("emission_factor")
    return table, results, answers


@pytest.fixture(scope="session")
def demo_analysis():
    from src.data import load_demo_data

    return analyse(load_demo_data())


@pytest.fixture(scope="session")
def minimal_analysis():
    """Only ts, it_kw and total_kw, and no weather: the smallest file users can upload."""
    from src import location
    from src.data import load_demo_data

    def offline(url, params):
        raise location.LocationError("offline in tests")

    real, location._get_json = location._get_json, offline  # never touch the network
    try:
        return analyse(load_demo_data()[["ts", "it_kw", "total_kw"]])
    finally:
        location._get_json = real


def open_page(page_file: str, analysis=None, timeout: int = 60) -> AppTest:
    """Open one analysis page in AppTest, with the results already in the session."""
    at = AppTest.from_file(APP, default_timeout=timeout)
    at.session_state["stage"] = "analysis"
    at.session_state["file_name"] = "dev.csv"
    if analysis is not None:
        table, results, answers = analysis
        at.session_state["data"] = table
        at.session_state["results"] = results
        at.session_state["answers"] = dict(answers)
    at.run()
    at.switch_page(str(PAGES / page_file)).run()
    return at
