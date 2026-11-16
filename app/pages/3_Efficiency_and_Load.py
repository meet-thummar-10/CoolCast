"""3 Efficiency & Load: how efficient the site is at different IT loads and in each month."""

import streamlit as st

from app.components import bar_chart, empty_state, kpi_card, line_chart
from app.formatting import fmt_pct
from app.page_utils import page_start, table
from src.metrics import pue_by_load

MIN_HOURS = 24  # a load band needs a day of data to count as best or worst

results = page_start("Efficiency & Load", "How efficient your site is at different IT loads and "
                                          "in each month, and what drives the overhead.")
df = table()
bands = pue_by_load(df)
solid = bands[bands["hours"] >= MIN_HOURS]
monthly = results["monthly"]

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)
if len(solid):
    best, worst = solid.loc[solid["pue"].idxmin()], solid.loc[solid["pue"].idxmax()]
    common = bands.loc[bands["hours"].idxmax()]
    with c1:
        kpi_card("Best PUE (by load)", f"{best['pue']:.3f}", "measured",
                 help=f"At IT load {best['load_bin']}")
    with c2:
        kpi_card("Worst PUE (by load)", f"{worst['pue']:.3f}", "measured",
                 help=f"At IT load {worst['load_bin']}")
    with c3:
        kpi_card("Most common load", common["load_bin"], "measured",
                 help=f"{common['hours']:,} hours")
with c4:
    b, w = monthly.loc[monthly["pue"].idxmin()], monthly.loc[monthly["pue"].idxmax()]
    kpi_card("Best and worst month", f"{b['month']} / {w['month']}", "measured",
             help=f"PUE {b['pue']:.3f} and {w['pue']:.3f}")

left, right = st.columns(2)
with left:
    line_chart(bands.rename(columns={"it_kw_mid": "IT load (kW)"}), "IT load (kW)", "pue",
               title="PUE by IT load", y_label="PUE")
    st.caption("PUE is usually higher at low load, because part of the overhead runs all the "
               "time whatever the servers do.")
with right:
    bar_chart(monthly.rename(columns={"month": "Month"}), "Month", "pue", title="PUE by month",
              y_label="PUE", highlight_max=True)

st.subheader("What drives your overhead")
split = results.get("overhead")
if not split:
    empty_state("Not enough complete hours to split the overhead.")
else:
    a, b, c = st.columns(3)
    with a:
        kpi_card("Always on", fmt_pct(split["always_on"], 0), "modelled",
                 help="Runs whatever the servers or the weather do (pumps at fixed speed, "
                      "losses, lighting)")
    with b:
        kpi_card("Follows the servers", fmt_pct(split["follows_servers"], 0), "modelled")
    with c:
        weather = split["follows_weather"]
        kpi_card("Follows the weather", "–" if weather is None else fmt_pct(weather, 0),
                 "modelled", help=None if weather is not None else
                 "No outdoor temperature was available")
    st.caption(f"Fit quality R² {split['r2']:.2f} (1.0 = perfect). A large \"always on\" share "
               "means the biggest savings come from equipment that does not need to run at full "
               "power all the time.")
