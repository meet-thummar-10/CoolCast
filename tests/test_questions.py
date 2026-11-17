from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.pipeline import STEPS, run_analysis
from app.questions import (
    QUESTIONS,
    TOTAL,
    answer_text,
    answered_count,
    check_answer,
    is_answered,
)
from src import location
from src.data import load_demo_data

APP = str(Path(__file__).resolve().parent.parent / "app" / "Home.py")
FULL = {"country": "India", "city": "Pune", "price": 8.0, "currency": "INR",
        "site_type": "hpc", "cooling_system": "water_chillers", "free_cooling": "no",
        "supply_temp_c": 22.0, "vfd": "some", "ups_mode": "double_conversion",
        "unused_servers": "sometimes", "can_change": "small"}


def questions(answers=None, index=None):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["stage"] = "questions"
    at.session_state["file_name"] = "my_site.csv"
    if answers is not None:
        at.session_state["answers"] = dict(answers)
    if index is not None:
        at.session_state["q_index"] = index
    return at.run()


# ------------------------------------------------------------ question logic


def test_ten_questions_in_order():
    assert TOTAL == 10
    assert QUESTIONS[0]["key"] == "location" and QUESTIONS[1]["key"] == "price"
    assert all(q.get("required") for q in QUESTIONS[:2])
    assert not any(q.get("required") for q in QUESTIONS[2:])


def test_answered_counts_i_dont_know():
    answers = {"country": "India", "city": "Pune", "price": 8, "currency": "INR",
               "vfd": None}
    assert answered_count(answers) == 3
    assert answer_text(6, answers) == "I don't know"
    assert not is_answered(0, {"country": "India", "city": "  "})


# ------------------------------------------------------------ screen


@pytest.fixture
def fake_map(monkeypatch):
    """The map service knows Frankfurt (Germany) and Pune (India); nothing else."""
    known = {("Frankfurt", "DE"): "Frankfurt am Main", ("Pune", "IN"): "Pune"}

    def fake(url, params):
        name = known.get((params.get("name"), params.get("countryCode")))
        return {"results": [{"name": name, "latitude": 1.0, "longitude": 2.0}]} if name else {}

    monkeypatch.setattr(location, "_get_json", fake)


def errors(at):
    return [e.value for e in at.error]


def test_next_checks_the_location_before_moving_on(fake_map):
    at = questions()
    assert not at.exception
    assert any("About your site" in m.value for m in at.markdown)
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 0 and "choose your country" in errors(at)[0]

    at.selectbox(key="q_country").set_value("Germany").run()
    assert at.session_state["answers"]["currency"] == "EUR"
    assert any("EUR" in m.value and "q-ok" in m.value for m in at.markdown)
    at.text_input(key="q_city").input("Qwertyville")
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 0 and "could not find 'Qwertyville'" in errors(at)[0]

    at.text_input(key="q_city").input("Frankfurt")
    at.button(key="next").click().run()  # no separate run after typing: Next saves it
    assert at.session_state["q_index"] == 1
    assert at.session_state["answers"]["city"] == "Frankfurt am Main"


def test_price_starts_empty_and_must_be_real():
    at = questions({"country": "India", "city": "Pune", "currency": "INR"}, 1)
    assert at.number_input(key="q_price").value is None  # nothing to delete before typing
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 1 and "price per kWh" in errors(at)[0]
    at.number_input(key="q_price").set_value(0.0)
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 1 and "more than 0" in errors(at)[0]
    at.number_input(key="q_price").set_value(8.5)
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 2
    assert at.session_state["answers"]["price"] == 8.5


def test_supply_temperature_must_be_realistic():
    at = questions(dict(FULL, supply_temp_c=22.0), 5)
    at.number_input(key="q_temp").set_value(80.0)
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 5 and "not a realistic" in errors(at)[0]
    at.number_input(key="q_temp").set_value(16.0)
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 6
    assert any("outside the usual" in w.value for w in at.warning)


def test_choice_question_needs_an_answer():
    answers = {k: v for k, v in FULL.items() if k != "vfd"}
    at = questions(answers, 6)
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 6 and "choose an option" in errors(at)[0]


def test_check_answer_rules():
    assert check_answer(0, {"country": "India", "city": "12"})[0]
    assert check_answer(0, {"country": "India", "city": "Pune"}) == (None, None)
    assert check_answer(5, {"supply_temp_c": None}) == (None, None)
    assert check_answer(5, {})[0]


def test_progress_after_the_two_required_questions():
    at = questions({"country": "India", "city": "Pune", "price": 8.0, "currency": "INR"}, 2)
    assert "2 of 10 answered" in at.get("progress")[0].proto.text


def test_choice_question_and_i_dont_know():
    at = questions(dict(FULL, vfd="all"), 6)  # variable-speed drives
    at.radio(key="q_vfd").set_value("idk").run()
    assert at.session_state["answers"]["vfd"] is None
    assert "10 of 10 answered" in at.get("progress")[0].proto.text
    at.button(key="next").click().run()
    assert at.session_state["q_index"] == 7


def test_review_screen_and_analyse():
    at = questions(FULL)
    assert at.session_state["q_index"] == TOTAL  # all answered: starts at the review
    assert any("Check your answers" in m.value for m in at.markdown)
    at.button(key="edit_5").click().run()
    assert at.session_state["q_index"] == 5
    at.session_state["q_index"] = TOTAL
    at.run()
    at.button(key="analyse").click().run()
    assert at.session_state["stage"] == "analysing"


def test_review_blocks_until_required_answers():
    at = questions({"country": "India"}, TOTAL)
    assert at.button(key="analyse").disabled


# ------------------------------------------------------------ analysis


def test_pipeline_on_development_data():
    seen = []
    results = run_analysis(load_demo_data(), FULL, {}, "dev.csv",
                           report=lambda i, s, d: seen.append((i, s)))
    assert {i for i, s in seen if s == "done"} == set(range(len(STEPS)))
    assert results["kpis"]["pue"] == pytest.approx(1.034, abs=0.0005)
    assert results["location"]["emission_factor"] == 0.675
    assert results["weather_source"] == "file"
    assert len(results["steps"]["steps"]) == 6


def test_pipeline_fetches_weather_when_the_file_has_none(monkeypatch):
    calls = []

    def fake(url, params):
        calls.append(url)
        if url == location.GEOCODE_URL:
            return {"results": [{"name": "Pune", "latitude": 18.5, "longitude": 73.9}]}
        times = pd.date_range(params["start_date"], params["end_date"]
                                                + " 23:00", freq="h")
        n = len(times)
        return {"hourly": {"time": list(times.strftime("%Y-%m-%dT%H:%M")),
                           "temperature_2m": [25.0] * n, "relative_humidity_2m": [60] * n}}

    monkeypatch.setattr(location, "_get_json", fake)
    location._weather_cached.cache_clear()
    df = load_demo_data().drop(columns=["temp_c", "humidity"])
    results = run_analysis(df, FULL, {}, "dev.csv")
    assert results["weather_source"] == "open-meteo"
    assert results["table"]["temp_c"].notna().mean() > 0.9
    assert location.WEATHER_URL in calls


def test_analysing_screen_runs_and_opens_the_analysis():
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["stage"] = "analysing"
    at.session_state["data"] = load_demo_data()
    at.session_state["file_name"] = "dev.csv"
    at.session_state["answers"] = dict(FULL)
    at.run()
    assert not at.exception
    assert at.session_state["results"]["kpis"]["pue"] == pytest.approx(1.034, abs=0.0005)
    assert at.session_state["answers"]["emission_factor"] == 0.675
    at.button(key="next").click().run()
    assert at.session_state["stage"] == "analysis"


def test_analysing_without_data_asks_to_start_again():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["stage"] = "analysing"
    at.run()
    assert at.error and at.button(key="restart")
