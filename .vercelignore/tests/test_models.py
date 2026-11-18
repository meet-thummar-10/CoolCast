import numpy as np
import pandas as pd
import pytest

from src.data import load_demo_data
from src.models import BASELINE, make_features, train_models


def synthetic(hours=24 * 30, weather=True):
    ts = pd.date_range("2024-01-01", periods=hours, freq="h")
    rng = np.random.default_rng(0)
    it = 1000 + 100 * np.sin(np.arange(hours) / 24 * 2 * np.pi)
    df = pd.DataFrame({"ts": ts, "it_kw": it, "total_kw": it * 1.3 + rng.normal(0, 5, hours)})
    if weather:
        df["temp_c"] = 20 + 5 * np.sin(np.arange(hours) / 24 * 2 * np.pi)
        df["humidity"] = 50.0
    return df


def test_one_row_per_model_and_best_is_lowest_mae():
    out = train_models(synthetic())
    assert list(out["metrics"].columns) == ["model", "mae", "rmse", "r2"]
    assert len(out["metrics"]) == 3
    assert out["best"] == out["metrics"].sort_values("mae").iloc[0]["model"]
    assert set(out["predictions"].columns) == {"ts", "actual", BASELINE, "linear_regression", "gradient_boosting"}


def test_test_period_comes_after_training():
    df = synthetic()
    out = train_models(df)
    data = make_features(df).dropna()
    n_train = len(data) - len(out["predictions"])
    assert out["predictions"]["ts"].min() > data["ts"].iloc[n_train - 1]


def test_works_without_weather_columns():
    df = synthetic(weather=False)
    assert "temp_c" not in make_features(df).columns
    assert len(train_models(df)["metrics"]) == 3


def test_lag_uses_clock_time_across_gaps():
    df = synthetic(hours=24 * 9).drop(index=[30])
    feats = make_features(df).set_index("ts")
    t = pd.Timestamp("2024-01-02 07:00")  # row 31, 24 h after row 7
    assert feats.loc[t, "lag_24h"] == pytest.approx(df.set_index("ts").loc[t - pd.Timedelta("24h"), "total_kw"])


def test_results_repeat():
    a = train_models(synthetic())["metrics"]
    b = train_models(synthetic())["metrics"]
    pd.testing.assert_frame_equal(a, b)


def test_missing_columns_or_too_little_data_raise():
    with pytest.raises(ValueError, match="it_kw"):
        train_models(synthetic().drop(columns="it_kw"))
    with pytest.raises(ValueError, match="48"):
        train_models(synthetic(hours=24 * 7 + 40))


def test_development_data_beats_baseline_for_cooling():
    out = train_models(load_demo_data(), target="mechanical_kw")
    m = out["metrics"].set_index("model")["mae"]
    assert m[BASELINE] == pytest.approx(2.66, abs=0.3)
    assert min(m["linear_regression"], m["gradient_boosting"]) < m[BASELINE]
