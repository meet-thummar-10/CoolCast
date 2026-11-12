import numpy as np
import pandas as pd
import pytest

from src.data import load_demo_data
from src.metrics import compute_kpis, interval_hours, pue_by_load


def table(it, total, start="2023-01-01", freq="h"):
    """Standard hourly table where all overhead is cooling, so total = it + cooling."""
    it = np.asarray(it, dtype=float)
    total = np.asarray(total, dtype=float)
    return pd.DataFrame({
        "ts": pd.date_range(start, periods=len(it), freq=freq),
        "it_kw": it,
        "cooling_kw": total - it,
        "pump_kw": 0.0,
        "hvac_kw": 0.0,
        "plug_kw": 0.0,
        "total_kw": total,
        "mechanical_kw": total - it,
    })


def test_issue_example():
    kpis = compute_kpis(table([100, 300], [120, 330]), tariff=8, emission_factor=0.7)
    assert kpis["pue"] == pytest.approx(1.125)  # ratio of sums, not the 1.15 average
    assert kpis["it_kwh"] == pytest.approx(400)
    assert kpis["total_kwh"] == pytest.approx(450)
    assert kpis["cost"] == pytest.approx(3600)
    assert kpis["co2_kg"] == pytest.approx(315)
    assert kpis["cue"] == pytest.approx(0.7875)
    assert kpis["cooling_share"] == pytest.approx(50 / 450)


def test_rows_with_missing_power_are_skipped():
    df = table([100, 300, 500], [120, 330, 600])
    df.loc[2, "total_kw"] = np.nan
    assert compute_kpis(df, 8, 0.7)["it_kwh"] == pytest.approx(400)


def test_works_with_only_it_and_total_power():
    df = table([100, 300], [120, 330])[["ts", "it_kw", "total_kw"]]
    kpis = compute_kpis(df, tariff=8, emission_factor=0.7)
    assert kpis["pue"] == pytest.approx(1.125)
    assert kpis["cooling_share"] is None
    assert pue_by_load(df)["hours"].sum() == 2


def test_energy_uses_the_time_step():
    df = table([100, 100], [110, 110], freq="15min")
    assert interval_hours(df) == 0.25
    assert compute_kpis(df, 8, 0.7)["it_kwh"] == pytest.approx(50)


def test_no_data_gives_none_ratios():
    kpis = compute_kpis(table([], []), 8, 0.7)
    assert kpis["pue"] is None and kpis["cue"] is None and kpis["total_kwh"] == 0


def test_pue_by_load():
    df = table([100, 100, 1000, 1000], [150, 150, 1100, 1100])
    out = pue_by_load(df, bins=2)
    assert list(out.columns) == ["load_bin", "it_kw_mid", "pue", "hours"]
    assert out["pue"].tolist() == pytest.approx([1.5, 1.1])
    assert out["hours"].tolist() == [2, 2]


def test_pue_by_load_skips_empty_bins():
    df = table([100, 1000], [110, 1100])
    assert len(pue_by_load(df, bins=10)) == 2


def test_demo_data_matches_cleaning_result():
    kpis = compute_kpis(load_demo_data(), tariff=8, emission_factor=0.675)
    assert kpis["pue"] == pytest.approx(1.0339, abs=1e-3)  # 2023 value in docs/data.md
    bins = pue_by_load(load_demo_data())
    assert bins["hours"].sum() == load_demo_data().dropna(subset=["total_kw"]).shape[0]
