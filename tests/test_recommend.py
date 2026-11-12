import math

import numpy as np
import pandas as pd
import pytest

from src.data import load_demo_data
from src.metrics import compute_kpis
from src.recommend import OPTIONS, overhead_split, recommend

DEMO = load_demo_data()
KPIS = compute_kpis(DEMO, tariff=8, emission_factor=0.675)
ANSWERS = {"price": 8, "currency": "INR", "site_type": "hpc", "cooling_system": "water_chillers",
           "free_cooling": "no", "supply_temp_c": 22, "vfd": "some",
           "ups_mode": "double_conversion", "unused_servers": "sometimes", "can_change": "small"}
LOCATION = {"emission_factor": 0.675, "free_cooling_hours": 6460}


def sig2(x):
    """Round to 2 significant figures, as the app shows ranges."""
    return round(x, 1 - math.floor(math.log10(abs(x)))) if x else 0


def steps(answers=None, location=LOCATION, df=DEMO, kpis=KPIS):
    out = recommend(df, kpis, {**ANSWERS, **(answers or {})}, location)
    return {s["id"]: s for s in out["steps"]}, {s["id"]: s["reason"] for s in out["skipped"]}


def mwh(step):
    return sig2(step["low_kwh"] / 1000), sig2(step["high_kwh"] / 1000)


def test_issue_example_ranges():
    found, skipped = steps()
    assert skipped == {}
    assert mwh(found["setpoint"]) == (55, 110)
    assert mwh(found["vfd"]) == (0, 110)
    assert sig2(found["servers"]["low_kwh"] / 1000) == 180  # ≈ 176 MWh per 1 % of IT
    assert found["servers"]["low_kwh"] / 1000 == pytest.approx(176.3, abs=0.1)
    assert found["servers"]["per"] == "1 % of IT power switched off"
    assert mwh(found["ups"]) == (0, 350)
    assert mwh(found["lighting"]) == (2.6, 6.5)
    assert found["free_cooling"]["low_kwh"] is None  # feasibility only, no range


def test_money_and_co2_follow_tariff_and_factor():
    s = steps()[0]["setpoint"]
    assert s["low_money"] == pytest.approx(s["low_kwh"] * 8)
    assert s["high_co2_kg"] == pytest.approx(s["high_kwh"] * 0.675)


def test_every_step_is_complete_and_labelled():
    for s in steps()[0].values():
        for key in ("title", "effort", "confidence", "found", "todo", "calc", "warning",
                    "sources"):
            assert s[key], (s["id"], key)
        assert s["effort"] in ("free", "small", "large")
        assert s["label"] == "estimate"


def test_no_total_of_steps_is_returned():
    out = recommend(DEMO, KPIS, ANSWERS, LOCATION)
    assert set(out) == {"steps", "skipped", "period_hours"}


@pytest.mark.parametrize("answers, gone", [
    ({"supply_temp_c": 27}, "setpoint"),
    ({"vfd": "all"}, "vfd"),
    ({"site_type": "colocation"}, "servers"),
    ({"unused_servers": "regularly"}, "servers"),
    ({"ups_mode": "eco"}, "ups"),
    ({"free_cooling": "water"}, "free_cooling"),
])
def test_answers_remove_steps_with_a_reason(answers, gone):
    found, skipped = steps(answers)
    assert gone not in found
    assert skipped[gone]


def test_unknown_supply_temperature_assumes_one_degree():
    found, _ = steps({"supply_temp_c": None})
    low, high = found["setpoint"]["low_kwh"], found["setpoint"]["high_kwh"]
    cooling = DEMO.dropna(subset=["it_kw", "total_kw"])["mechanical_kw"].sum()
    assert (low, high) == pytest.approx((cooling * 0.02, cooling * 0.04))


def test_supply_below_18_counts_headroom_only_from_18():
    a = steps({"supply_temp_c": 15})[0]["setpoint"]["high_kwh"]
    b = steps({"supply_temp_c": 18})[0]["setpoint"]["high_kwh"]
    assert a == pytest.approx(b)


def test_mixed_ups_uses_half_the_range():
    assert steps({"ups_mode": "mix"})[0]["ups"]["high_kwh"] == pytest.approx(
        steps()[0]["ups"]["high_kwh"] / 2)


def test_only_it_and_total_power_still_gives_steps():
    df = DEMO[["ts", "it_kw", "total_kw"]]
    found, skipped = steps(df=df, kpis=compute_kpis(df, 8, 0.675), location={})
    assert set(found) == {"servers", "ups"}
    assert set(skipped) == {"setpoint", "vfd", "lighting", "free_cooling"}


def test_free_cooling_feasibility():
    suitable = steps(location={**LOCATION, "free_cooling_hours": 6460})[0]["free_cooling"]
    assert "Suitable" in suitable["calc"]
    poor = steps(location={**LOCATION, "free_cooling_hours": 400})[0]["free_cooling"]
    assert "Not very suitable" in poor["calc"]


def test_answer_options_cover_every_question():
    assert set(OPTIONS) == {"site_type", "cooling_system", "free_cooling", "vfd", "ups_mode",
                            "unused_servers", "can_change"}


def test_overhead_split_on_development_data():
    split = overhead_split(DEMO)
    assert split["always_on"] == pytest.approx(0.83, abs=0.01)
    assert split["follows_servers"] == pytest.approx(0.02, abs=0.01)
    assert split["follows_weather"] == pytest.approx(0.15, abs=0.01)
    assert split["r2"] == pytest.approx(0.50, abs=0.01)
    assert sum(v for k, v in split.items() if k.startswith(("always", "follows"))) == \
        pytest.approx(1)


def test_overhead_split_recovers_a_known_pattern():
    n = 24 * 30
    rng = np.random.default_rng(0)
    it = 1000 + 200 * rng.random(n)
    temp = 5 + 25 * rng.random(n)
    overhead = 50 + 0.02 * it + 3 * np.clip(temp - 10, 0, None)
    df = pd.DataFrame({"ts": pd.date_range("2024-01-01", periods=n, freq="h"), "it_kw": it,
                       "total_kw": it + overhead, "temp_c": temp})
    split = overhead_split(df)
    parts = np.array([50 * n, 0.02 * it.sum(), 3 * np.clip(temp - 10, 0, None).sum()])
    assert [split["always_on"], split["follows_servers"], split["follows_weather"]] == \
        pytest.approx(parts / parts.sum(), abs=1e-6)
    assert split["r2"] == pytest.approx(1)


def test_overhead_split_without_weather_or_data():
    split = overhead_split(DEMO.drop(columns=["temp_c"]))
    assert split["follows_weather"] is None
    assert split["always_on"] + split["follows_servers"] == pytest.approx(1)
    assert overhead_split(DEMO.head(10)) is None
