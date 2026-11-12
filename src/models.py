"""Forecast models: predict a site's hourly power and report their accuracy.

Users upload their own data, so only ``ts``, ``it_kw`` and ``total_kw`` are
guaranteed. Outdoor ``temp_c`` and ``humidity`` are used only when present.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

RANDOM_STATE = 0
TEST_SHARE = 0.2
LAG_HOURS = 24
WEATHER = ("temp_c", "humidity")
BASELINE = "baseline"
MIN_HOURS = 48


def make_features(df: pd.DataFrame, target: str = "total_kw") -> pd.DataFrame:
    """Return ``ts``, the target and the model features for every hour.

    Features: hour, day of week, ``it_kw`` and its change since the same
    hour yesterday, the target 24 hours and 7 days earlier (``lag_24h``,
    ``lag_168h``) and, when the file has them, outdoor temperature (and its
    change since yesterday) and humidity. Month is left out on purpose: the
    test period holds months the model never saw in training.
    """
    if target not in df or "it_kw" not in df:
        raise ValueError(f"The data needs 'ts', 'it_kw' and '{target}'.")
    data = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
    out = pd.DataFrame(index=data.index)

    def ago(col: str, hours: int) -> pd.Series:
        # Shift by clock time, not by rows, so gaps in the data do not misalign it.
        return data[col].shift(freq=f"{hours}h").reindex(data.index)

    out["hour"] = data.index.hour
    out["day_of_week"] = data.index.day_of_week
    out["it_kw"] = data["it_kw"]
    out["it_change_24h"] = data["it_kw"] - ago("it_kw", LAG_HOURS)
    out["lag_24h"] = ago(target, LAG_HOURS)
    out["lag_168h"] = ago(target, 7 * LAG_HOURS)
    for col in WEATHER:
        if col in data and data[col].notna().any():
            out[col] = data[col]
    if "temp_c" in out:
        out["temp_change_24h"] = data["temp_c"] - ago("temp_c", LAG_HOURS)
    out["target"] = data[target]
    return out.reset_index()


def _scores(actual: pd.Series, predicted: np.ndarray) -> dict:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
    }


def train_models(df: pd.DataFrame, target: str = "total_kw") -> dict:
    """Train the forecast models on the first 80 % of hours, test on the rest.

    Returns ``{models, metrics, predictions, best}``:
    - ``models``: name -> fitted model (the baseline has none)
    - ``metrics``: DataFrame ``model, mae, rmse, r2`` (kW), best first
    - ``predictions``: DataFrame ``ts, actual`` and one column per model
    - ``best``: name of the model with the lowest MAE
    """
    data = make_features(df, target).dropna().reset_index(drop=True)
    if len(data) < MIN_HOURS:
        raise ValueError(f"Not enough complete hours to train a forecast (need at least {MIN_HOURS}, after the first week).")
    split = int(len(data) * (1 - TEST_SHARE))
    train, test = data.iloc[:split], data.iloc[split:]
    features = [c for c in data.columns if c not in ("ts", "target")]

    models = {
        "linear_regression": LinearRegression(),
        "gradient_boosting": HistGradientBoostingRegressor(random_state=RANDOM_STATE),
    }
    predictions = pd.DataFrame({"ts": test["ts"].to_numpy(), "actual": test["target"].to_numpy()})
    predictions[BASELINE] = test["lag_24h"].to_numpy()
    for name, model in models.items():
        model.fit(train[features], train["target"])
        predictions[name] = model.predict(test[features])

    rows = [{"model": name, **_scores(predictions["actual"], predictions[name])}
            for name in [BASELINE, *models]]
    metrics = pd.DataFrame(rows).sort_values("mae", kind="stable").reset_index(drop=True)
    return {
        "models": models,
        "metrics": metrics,
        "predictions": predictions,
        "best": str(metrics.loc[0, "model"]),
    }
