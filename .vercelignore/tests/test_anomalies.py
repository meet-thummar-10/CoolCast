import numpy as np
import pandas as pd
import pytest

from src.anomalies import COLUMNS, best_predictions, flag_anomalies
from src.data import load_demo_data
from src.models import train_models


def table(actual):
    return pd.DataFrame({"ts": pd.date_range("2024-01-01", periods=len(actual), freq="h"),
                         "total_kw": np.asarray(actual, dtype=float)})


def test_issue_example():
    actual = [10, 10, 10, 10, 20, 20, 20, 10, 10, 10]
    out = flag_anomalies(table(actual), [10] * 10, tariff=8, threshold_kw=5)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["start"] == pd.Timestamp("2024-01-01 04:00")
    assert row["end"] == pd.Timestamp("2024-01-01 06:00")
    assert row["hours"] == 3
    assert row["excess_kwh"] == pytest.approx(30)
    assert row["excess_cost"] == pytest.approx(240)


def test_nothing_above_threshold_gives_empty_table():
    out = flag_anomalies(table([10] * 10), [10] * 10, tariff=8, threshold_kw=5)
    assert out.empty and list(out.columns) == COLUMNS


def test_largest_period_first():
    actual = [30, 10, 10, 20, 20, 10]
    out = flag_anomalies(table(actual), [10] * 6, tariff=1, threshold_kw=5)
    assert out["excess_kwh"].tolist() == pytest.approx([20, 20])
    assert out["hours"].tolist() == [1, 2]


def test_a_gap_in_time_splits_a_period():
    df = table([20, 20, 20, 20]).drop(index=1)  # 01:00 missing
    out = flag_anomalies(df, [10, 10, 10], tariff=1, threshold_kw=5)
    assert out["hours"].sort_values().tolist() == [1, 2]


def test_missing_hours_are_never_flagged():
    out = flag_anomalies(table([20, np.nan, 20]), [10, 10, 10], tariff=1, threshold_kw=5)
    assert out["hours"].tolist() == [1, 1]


def test_default_threshold_is_three_standard_deviations():
    rng = np.random.default_rng(0)
    actual = 100 + rng.normal(0, 1, 500)
    actual[250] = 150
    out = flag_anomalies(table(actual), [100] * 500, tariff=1)
    assert out["start"].tolist() == [pd.Timestamp("2024-01-01") + pd.Timedelta(hours=250)]


def test_predictions_by_time_and_wrong_length():
    df = table([10, 30, 10])
    preds = pd.Series([10.0, 10.0], index=df["ts"][1:])  # first hour has no forecast
    assert flag_anomalies(df, preds, tariff=1, threshold_kw=5)["hours"].tolist() == [1]
    with pytest.raises(ValueError, match="one value per row"):
        flag_anomalies(df, [10, 10], tariff=1)


def test_works_with_train_models_on_development_data():
    df = load_demo_data()
    result = train_models(df, target="mechanical_kw")
    out = flag_anomalies(df, best_predictions(result), tariff=8, target="mechanical_kw")
    assert list(out.columns) == COLUMNS
    assert (out["excess_kwh"] > 0).all()
    assert out["excess_kwh"].is_monotonic_decreasing
