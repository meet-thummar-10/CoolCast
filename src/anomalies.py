"""Anomaly flags: periods where power was much higher than the forecast expected.

A flagged period is "worth investigating", not proof of a fault.
"""

import numpy as np
import pandas as pd

from src.metrics import interval_hours

COLUMNS = ["start", "end", "hours", "excess_kwh", "excess_cost"]
DEFAULT_K = 3  # flag hours more than 3 standard deviations above the forecast


def best_predictions(result: dict) -> pd.Series:
    """The best model's test-period forecast from ``train_models()``, indexed by time."""
    preds = result["predictions"]
    return preds.set_index("ts")[result["best"]]


def flag_anomalies(df: pd.DataFrame, predictions, tariff: float, threshold_kw: float | None = None,
                   target: str = "total_kw") -> pd.DataFrame:
    """Find periods where actual power was well above the forecast.

    Args:
        df: standard hourly table with ``ts`` and the ``target`` column
        predictions: a Series indexed by time (e.g. ``best_predictions(result)``),
            or an array with one value per row of ``df``
        tariff: electricity price per kWh in the user's currency
        threshold_kw: an hour is flagged when actual − predicted is above this;
            default 3 × the standard deviation of the residuals
        target: the column that was forecast

    Returns a DataFrame ``start, end, hours, excess_kwh, excess_cost``, one row
    per period of consecutive flagged hours, largest ``excess_kwh`` first.
    """
    data = df[["ts", target]].sort_values("ts").reset_index(drop=True)
    if isinstance(predictions, pd.Series) and isinstance(predictions.index, pd.DatetimeIndex):
        predicted = predictions.reindex(data["ts"]).to_numpy(dtype=float)
    else:
        predicted = np.asarray(predictions, dtype=float)
        if len(predicted) != len(data):
            raise ValueError("predictions must have one value per row of df, or a time index")
    residual = data[target].to_numpy(dtype=float) - predicted

    if threshold_kw is None:
        if np.isnan(residual).all():
            return pd.DataFrame(columns=COLUMNS)
        threshold_kw = DEFAULT_K * float(np.nanstd(residual))
    flagged = residual > threshold_kw  # NaN compares False: missing hours are never flagged

    step = pd.Timedelta(hours=interval_hours(data))
    periods = []
    start = None
    for i, is_flagged in enumerate(flagged):
        new_run = start is None or data["ts"][i] - data["ts"][i - 1] != step
        if is_flagged and new_run:
            start = i
        elif not is_flagged:
            start = None
            continue
        if i + 1 == len(data) or not flagged[i + 1] or data["ts"][i + 1] - data["ts"][i] != step:
            excess = float(residual[start:i + 1].sum() * step / pd.Timedelta(hours=1))
            periods.append({"start": data["ts"][start], "end": data["ts"][i], "hours": i - start + 1,
                            "excess_kwh": excess, "excess_cost": excess * tariff})
            start = None

    out = pd.DataFrame(periods, columns=COLUMNS)
    return out.sort_values("excess_kwh", ascending=False, kind="stable").reset_index(drop=True)
