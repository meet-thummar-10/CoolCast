"""4 Cooling & Weather: how outdoor weather drives cooling, and free-cooling hours."""

import pandas as pd
import streamlit as st

from app.components import bar_chart, empty_state, heatmap, kpi_card, scatter
from app.formatting import fmt_pct
from app.page_utils import has, page_start, table
from src.location import FREE_COOLING_LIMIT_C

SOURCES = {"file": "From your file",
           "open-meteo": "Past weather for your city (Open-Meteo, ERA5)",
           "none": "No weather available"}
SUITABLE_H = 3000

results = page_start("Cooling & Weather", "How outdoor weather drives your cooling, and how many "
                                          "hours your climate could cool for free.")
df = table()
source = results.get("weather_source", "none")
st.caption(f"Weather: {SOURCES.get(source, source)}")
if not has(df, "temp_c"):
    empty_state("No outdoor temperature is available (your file has none and past weather could "
                "not be fetched), so this page cannot be shown.")
    st.stop()

if has(df, "mechanical_kw"):
    power, label = "mechanical_kw", "Cooling system (kW)"
else:
    df = df.assign(overhead_kw=df["total_kw"] - df["it_kw"])
    power, label = "overhead_kw", "Overhead (kW)"
    st.info("Your file has no cooling columns, so this page uses all overhead power (total − IT) "
            "instead of cooling power.", icon=":material/info:")

rows = df.dropna(subset=[power, "temp_c"])
link = rows[power].corr(rows["temp_c"])
cold, hot = rows[rows["temp_c"] < -10][power], rows[rows["temp_c"] > 30][power]
share = (rows[power] / rows["total_kw"]).groupby(rows["ts"].dt.to_period("M")).mean()

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)
with c1:
    strength = "strong" if abs(link) >= 0.5 else "moderate" if abs(link) >= 0.3 else "weak"
    kpi_card("Link with temperature", f"{link:.2f} ({strength})", "measured",
             help="Correlation from −1 to 1: how closely cooling power follows outdoor "
                  "temperature")
with c2:
    kpi_card("Power below −10 °C", f"{cold.mean():.1f} kW" if len(cold) else "–", "measured")
with c3:
    kpi_card("Power above 30 °C", f"{hot.mean():.1f} kW" if len(hot) else "–", "measured")
with c4:
    kpi_card("Highest share of total", f"{share.max():.1%} ({share.idxmax()})", "measured")

left, right = st.columns(2)
with left:
    sample = rows.sample(min(len(rows), 3000), random_state=0)
    scatter(sample.rename(columns={"temp_c": "temp_c", power: label}), "temp_c", label,
            title=f"{label.split(' (')[0]} vs outdoor temperature")
with right:
    grid = rows.pivot_table(index=rows["ts"].dt.hour, columns=rows["ts"].dt.strftime("%m %b"),
                            values=power, aggfunc="mean")
    grid.columns = [c[3:] for c in grid.columns]
    heatmap(grid, title="When is it highest? (average kW by hour and month)", x_label="Month",
            y_label="Hour of day", z_label="kW")

monthly = pd.DataFrame({"Month": share.index.astype(str), power: share.to_numpy() * 100})
bar_chart(monthly, "Month", power, title="Share of total power, by month", y_label="%")

st.subheader("Free cooling")
hours = results["location"].get("free_cooling_hours")
if hours is None:
    empty_state("Free-cooling hours need outdoor temperature and humidity.")
else:
    a, b = st.columns([1, 2])
    with a:
        kpi_card("Free-cooling hours a year", f"{hours:,.0f}", "modelled",
                 help=f"Hours with wet-bulb temperature below {FREE_COOLING_LIMIT_C} °C (55 °F)")
    with b:
        verdict = "suitable" if hours >= SUITABLE_H else "not very suitable"
        st.markdown(f"Guideline: climates with **{SUITABLE_H:,} or more** such hours suit "
                    f"water-side free cooling (ENERGY STAR / US DOE). Your climate is "
                    f"**{verdict}** ({fmt_pct(hours / 8760, 0)} of the year).")
