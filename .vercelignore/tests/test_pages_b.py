import pytest
from conftest import open_page

PAGES = {"4_Cooling_and_Weather.py": "Cooling & Weather", "5_Anomalies.py": "Anomalies"}


@pytest.mark.parametrize("page, title", PAGES.items())
def test_pages_load_with_development_data(page, title, demo_analysis):
    at = open_page(page, demo_analysis)
    assert not at.exception, page
    assert at.title[0].value == title


@pytest.mark.parametrize("page", PAGES)
def test_pages_load_with_only_it_and_total_power(page, minimal_analysis):
    assert not open_page(page, minimal_analysis).exception


@pytest.mark.parametrize("page", PAGES)
def test_pages_without_analysis_ask_for_upload(page):
    assert open_page(page).button(key="no_results_upload")


def metrics(at):
    return {m.label: m.value for m in at.metric}


def test_cooling_page_free_cooling_hours(demo_analysis):
    at = open_page("4_Cooling_and_Weather.py", demo_analysis)
    hours = demo_analysis[1]["location"]["free_cooling_hours"]
    assert metrics(at)["Free-cooling hours a year"] == f"{hours:,.0f}"
    assert any("From your file" in c.value for c in at.caption)


def test_cooling_page_without_weather_explains_why(minimal_analysis):
    at = open_page("4_Cooling_and_Weather.py", minimal_analysis)
    assert any("No outdoor temperature" in i.value for i in at.info)


def test_anomalies_page_lists_the_flagged_periods(demo_analysis):
    at = open_page("5_Anomalies.py", demo_analysis)
    assert metrics(at)["Periods flagged"] == str(len(demo_analysis[1]["anomalies"]))
    assert at.dataframe[0].value.shape[0] == len(demo_analysis[1]["anomalies"])
