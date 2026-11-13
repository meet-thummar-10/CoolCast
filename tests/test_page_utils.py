import pytest
from streamlit.testing.v1 import AppTest


def page():
    from app.page_utils import money, page_start

    results = page_start("Test page", "A page for the tests.")
    import streamlit as st

    st.metric("Cost", money(results["kpis"]["cost"]))
    st.metric("Setpoint high", money(results["steps"]["steps"][0]["high_money"]))


def test_no_results_shows_a_message_and_stops():
    at = AppTest.from_function(page, default_timeout=30).run()
    assert not at.exception
    assert "no analysis yet" in at.info[0].value
    assert at.button(key="no_results_upload")
    assert not at.metric


def test_money_follows_the_sidebar_price(demo_analysis):
    table, results, answers = demo_analysis
    at = AppTest.from_function(page, default_timeout=30)
    at.session_state["data"], at.session_state["results"] = table, results
    at.session_state["answers"] = dict(answers)
    at.run()
    assert at.metric[0].value == "₹14.1 crore"
    at.session_state["tariff"] = 4.0  # the user halves the price in the sidebar
    at.run()
    assert at.metric[0].value == "₹7.05 crore"
    assert at.metric[1].value == "₹4.41 lakh"


def test_minimal_file_analysis_works(minimal_analysis):
    table, results, _ = minimal_analysis
    assert set(table.columns) == {"ts", "it_kw", "total_kw"}
    assert results["weather_source"] == "none"
    assert {s["id"] for s in results["steps"]["steps"]} == {"servers", "ups"}
    assert results["kpis"]["pue"] == pytest.approx(1.034, abs=0.001)
