import pytest
from conftest import open_page

PAGES = {"1_Data.py": "Data", "2_Energy_and_Cost.py": "Energy & Cost",
         "3_Efficiency_and_Load.py": "Efficiency & Load"}


@pytest.mark.parametrize("page, title", PAGES.items())
def test_pages_load_with_development_data(page, title, demo_analysis):
    at = open_page(page, demo_analysis)
    assert not at.exception, page
    assert at.title[0].value == title


@pytest.mark.parametrize("page", PAGES)
def test_pages_load_with_only_it_and_total_power(page, minimal_analysis):
    at = open_page(page, minimal_analysis)
    assert not at.exception, page


@pytest.mark.parametrize("page", PAGES)
def test_pages_without_analysis_ask_for_upload(page):
    at = open_page(page)
    assert not at.exception
    assert at.button(key="no_results_upload")


def metric(at, label):
    return next(m.value for m in at.metric if m.label.startswith(label))


def test_data_page_numbers(demo_analysis):
    at = open_page("1_Data.py", demo_analysis)
    assert metric(at, "Quality grade") == "B"
    assert metric(at, "Missing hours") == "623"


def test_energy_page_numbers_and_price_change(demo_analysis):
    at = open_page("2_Energy_and_Cost.py", demo_analysis)
    assert metric(at, "PUE") == "1.034"
    assert metric(at, "Electricity cost") == "₹14.1 crore"
    at.session_state["tariff"] = 4.0
    at.run()
    assert metric(at, "Electricity cost") == "₹7.05 crore"


def test_overhead_breakdown_needs_part_columns(minimal_analysis):
    at = open_page("2_Energy_and_Cost.py", minimal_analysis)
    assert any("Add columns for cooling" in i.value for i in at.info)


def test_efficiency_page_overhead_split(demo_analysis):
    at = open_page("3_Efficiency_and_Load.py", demo_analysis)
    assert metric(at, "Always on") == "83%"
    assert metric(at, "Follows the weather") == "15%"
