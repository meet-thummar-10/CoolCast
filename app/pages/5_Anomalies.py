"""5 Anomalies: periods that used more energy than the forecast expected."""

import pandas as pd
import streamlit as st

from app.components import INK, empty_state, kpi_card, line_chart
from app.formatting import fmt_energy
from app.page_utils import money, page_start

results = page_start("Anomalies", "Periods that used much more energy than the forecast "
                                  "expected. Each one is worth investigating, but it is not "
                                  "proof of a fault.")
anomalies = results.get("anomalies")
fc = results.get("forecast")
if fc is None:
    empty_state("Anomalies need a forecast, and there was not enough data to train one.")
    st.stop()

n = 0 if anomalies is None else len(anomalies)
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Periods flagged", f"{n}", "modelled")
with c2:
    kpi_card("Extra energy", fmt_energy(anomalies["excess_kwh"].sum()) if n else "0 kWh",
             "modelled")
with c3:
    kpi_card("Extra cost", money(anomalies["excess_cost"].sum()) if n else money(0), "modelled")
st.caption("A period is flagged when actual power is more than 3 standard deviations above the "
           "forecast. Checked over the test period of the forecast (the last 20 % of your data).")

preds = fc["predictions"]
chart = pd.DataFrame({"ts": preds["ts"], "actual": preds["actual"],
                      "forecast": preds[fc["best"]]})
fig = line_chart(chart, "ts", ["actual", "forecast"], title="Actual vs expected power",
                 y_label="kW", show=False)
for _, row in (anomalies.iterrows() if n else []):
    fig.add_vrect(x0=row["start"] - pd.Timedelta(minutes=30),
                  x1=row["end"] + pd.Timedelta(minutes=30), fillcolor="#DC2626", opacity=0.25,
                  line_width=0)
fig.update_layout(font_color=INK)
st.plotly_chart(fig)

st.subheader("Flagged periods")
if not n:
    empty_state("No period used much more energy than expected. That is good news.")
else:
    show = anomalies.assign(extra_energy=anomalies["excess_kwh"].map(fmt_energy),
                            extra_cost=anomalies["excess_cost"].map(money))
    st.dataframe(show[["start", "end", "hours", "extra_energy", "extra_cost"]].rename(columns={
        "start": "Start", "end": "End", "hours": "Hours", "extra_energy": "Extra energy",
        "extra_cost": "Extra cost"}), hide_index=True)
