"""6 Forecast & Planning: how well we can predict the site's power, week by week."""

import pandas as pd
import streamlit as st

from app.components import empty_state, kpi_card, line_chart
from app.page_utils import page_start

NAMES = {"baseline": "Same hour yesterday (baseline)", "linear_regression": "Linear regression",
         "gradient_boosting": "Gradient boosting"}

results = page_start("Forecast & Planning", "How well CoolCast can predict your power hour by "
                                            "hour, tested on the last 20 % of your data.")
fc = results.get("forecast")
if fc is None:
    empty_state("Not enough complete hours to train a forecast (at least about 9 days are needed).")
    st.stop()

target = results.get("forecast_target", "total_kw")
what = "cooling-system power" if target == "mechanical_kw" else "total facility power"
metrics = fc["metrics"].set_index("model")
best = fc["best"]
base = metrics.loc["baseline", "mae"]

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    kpi_card("Best model", NAMES.get(best, best), "modelled")
with c2:
    kpi_card("Average error", f"{metrics.loc[best, 'mae']:.1f} kW", "modelled",
             help="Mean absolute error on the test period")
with c3:
    gain = (base - metrics.loc[best, "mae"]) / base if base else 0
    kpi_card("Better than \"same as yesterday\"", f"{gain:.0%}", "modelled")
st.caption(f"Forecasting {what}. On average the best forecast is off by "
           f"{metrics.loc[best, 'mae']:.1f} kW; the simple \"same hour yesterday\" guess is off by "
           f"{base:.1f} kW.")

preds = fc["predictions"]
weeks = preds["ts"].dt.to_period("W").drop_duplicates().tolist()
labels = [f"{w.start_time:%d %b %Y} – {w.end_time:%d %b %Y}" for w in weeks]
peak = preds.groupby(preds["ts"].dt.to_period("W"))["actual"].max().idxmax()
week = st.selectbox("Week", range(len(weeks)), index=weeks.index(peak),
                    format_func=labels.__getitem__, key="forecast_week",
                    help="Starts on the week with the highest power")
shown = preds[preds["ts"].dt.to_period("W") == weeks[week]]
chart = pd.DataFrame({"ts": shown["ts"], "actual": shown["actual"], "forecast": shown[best]})
line_chart(chart, "ts", ["actual", "forecast"], title=f"Actual vs forecast: {labels[week]}",
           y_label="kW")

st.subheader("How accurate is each model?")
table = fc["metrics"].assign(model=lambda m: m["model"].map(NAMES).fillna(m["model"]))
st.dataframe(table.rename(columns={"model": "Model", "mae": "Average error (kW)",
                                   "rmse": "RMSE (kW)", "r2": "R²"}).round(2), hide_index=True)
st.caption("Lower error is better. R² near 1 means the model explains most of the ups and downs.")
