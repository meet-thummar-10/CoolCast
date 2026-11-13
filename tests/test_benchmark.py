import numpy as np
import pandas as pd
import pytest

from src.benchmark import benchmark_pue, load_benchmarks, monthly_pue
from src.data import load_demo_data


def site(pue, hours=24 * 60, it=1000.0):
    return pd.DataFrame({"ts": pd.date_range("2024-01-01", periods=hours, freq="h"),
                         "it_kw": it, "total_kw": it * pue})


def test_development_data():
    out = benchmark_pue(load_demo_data(), tariff=8)
    assert out["pue"] == pytest.approx(1.034, abs=0.0005)
    assert out["month_min"] == pytest.approx(1.019, abs=0.001)
    assert out["month_max"] == pytest.approx(1.052, abs=0.001)
    assert out["avoided_kwh"] / 1000 == pytest.approx(8_300, rel=0.01)
    assert out["avoided_money"] == pytest.approx(out["avoided_kwh"] * 8)
    assert out["low_pue_warning"] is True


def test_reference_rows():
    refs = benchmark_pue(site(1.5), tariff=1)["references"].set_index("name")
    assert list(refs.index) == ["Your site", "Google fleet", "Largest facilities", "Global average"]
    assert refs.loc["Google fleet", "overhead_per_100"] == pytest.approx(9)
    assert refs.loc["Global average", "pue"] == 1.52
    assert refs.loc["Your site", "overhead_for_you_kwh"] == pytest.approx(0.5 * 1000 * 24 * 60)


def test_worse_than_average_gives_negative_avoided_energy():
    out = benchmark_pue(site(1.8), tariff=1)
    assert out["avoided_kwh"] < 0
    assert out["low_pue_warning"] is False


def test_every_benchmark_has_a_source():
    for key, ref in load_benchmarks().items():
        assert ref["source"] and ref["link"].startswith("https://"), key
        assert 1 <= ref["pue"] < 3 and 2020 <= ref["year"] <= 2030, key


def test_monthly_pue_ignores_months_with_less_than_a_week():
    df = site(1.2, hours=24 * 31 + 24 * 3)  # January plus 3 days of February
    df.loc[df["ts"].dt.month == 2, "total_kw"] = 3000.0
    months = monthly_pue(df)
    assert len(months) == 1 and months.iloc[0] == pytest.approx(1.2)


def test_no_usable_hours_raises():
    df = site(1.2).assign(total_kw=np.nan)
    with pytest.raises(ValueError, match="PUE"):
        benchmark_pue(df, tariff=1)
