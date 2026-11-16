import pytest
from conftest import open_page

PAGES = {"6_Forecast_and_Planning.py": "Forecast & Planning",
         "7_How_to_reduce_your_cost.py": "How to reduce your cost",
         "8_Savings_calculator.py": "Savings calculator"}


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


def test_forecast_page_shows_the_best_model(demo_analysis):
    at = open_page("6_Forecast_and_Planning.py", demo_analysis)
    assert metrics(at)["Best model"] == "Gradient boosting"


def test_setpoint_card_and_filter(demo_analysis):
    at = open_page("7_How_to_reduce_your_cost.py", demo_analysis)
    assert "55 – 110 MWh" in [m.value for m in at.metric]
    titles = [m.value for m in at.markdown if m.value.startswith("####")]
    assert len(titles) == 5  # "small investments" answer hides the larger project
    at.radio(key="effort_filter").set_value("free").run()
    titles = [m.value for m in at.markdown if m.value.startswith("####")]
    assert len(titles) == 3
    at.radio(key="effort_filter").set_value("large").run()
    assert len([m for m in at.markdown if m.value.startswith("####")]) == 6


def test_no_total_of_steps_on_the_page(demo_analysis):
    at = open_page("7_How_to_reduce_your_cost.py", demo_analysis)
    assert not any("total" in m.label.lower() for m in at.metric)


def test_calculator_issue_example(demo_analysis):
    at = open_page("8_Savings_calculator.py", demo_analysis)
    at.number_input(key="calc_it").set_value(17_048.0).run()
    at.number_input(key="calc_pue").set_value(1.034).run()
    assert metrics(at)["Energy"] == "29 – 87 MWh"
    assert at.success  # likely
    at.number_input(key="calc_cut_low").set_value(0.0).run()
    assert any("Uncertain" in w.value for w in at.warning)
