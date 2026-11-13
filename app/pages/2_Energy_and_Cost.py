"""2 Energy & Cost: how much energy the site used, what it cost and its CO2."""

import pandas as pd
import streamlit as st

from app.components import bar_chart, empty_state, kpi_card
from app.formatting import fmt_co2, fmt_energy, fmt_pct
from app.page_utils import has, money, page_start, table

PARTS = {"cooling_kw": "Cooling plant", "pump_kw": "Pumps", "hvac_kw": "Air handling / fans",
         "plug_kw": "Lights and plugs", "other_kw": "Other non-IT"}

results = page_start("Energy & Cost", "How much energy your site used, what it cost and how much "
                                      "CO₂ it caused. Overhead is everything that is not IT.")
df = table()
k = results["kpis"]

c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("PUE", f"{k['pue']:.3f}", "measured",
             help="Total energy ÷ IT energy over the whole period. Lower is better; 1.0 is perfect.")
with c2:
    kpi_card("Total energy", fmt_energy(k["total_kwh"]), "measured")
with c3:
    kpi_card("Electricity cost", money(k["cost"]), "assumed",
             help="Total energy × your electricity price (change it in the sidebar)")
c4, c5, _ = st.columns(3)
with c4:
    kpi_card("CO₂ emitted", fmt_co2(k["co2_kg"]), "assumed",
             help="Total energy × your grid's CO₂ factor (change it in the sidebar)")
with c5:
    cue = "–" if k["cue"] is None else f"{k['cue']:.2f}"
    kpi_card("CUE (kg CO₂ per kWh of IT)", cue, "assumed")

overhead = k["total_kwh"] - k["it_kwh"]
st.caption(f"Overhead (cooling, power losses, lighting…): {fmt_energy(overhead)}, "
           f"{fmt_pct(overhead / k['total_kwh'])} of all energy"
           + ("" if k["cooling_share"] is None else
              f"; the cooling system alone is {fmt_pct(k['cooling_share'])}."))

monthly = results["monthly"]
chart = pd.DataFrame({"Month": monthly["month"], "it_kw": monthly["it_kwh"] / 1000,
                      "overhead_kw": (monthly["total_kwh"] - monthly["it_kwh"]) / 1000})
left, right = st.columns(2)
with left:
    bar_chart(chart, "Month", ["it_kw", "overhead_kw"], title="Energy per month", y_label="MWh")
with right:
    bar_chart(chart, "Month", "overhead_kw", title="Overhead per month (highest highlighted)",
              y_label="MWh", highlight_max=True)

st.subheader("Where the overhead goes")
parts = [c for c in PARTS if has(df, c)]
if not parts:
    empty_state("Your file has only IT and total power. Add columns for cooling, pumps, fans or "
                "lights to see where the overhead goes.")
else:
    rows = df.dropna(subset=["it_kw", "total_kw", *parts])
    energy = {PARTS[c]: rows[c].sum() / 1000 for c in parts}
    rest = (rows["total_kw"] - rows["it_kw"]).sum() / 1000 - sum(energy.values())
    if rest > 0.005 * sum(energy.values()):
        energy["Not split in your file"] = rest
    split = pd.DataFrame({"Part": list(energy), "overhead_kw": list(energy.values())})
    bar_chart(split.sort_values("overhead_kw", ascending=False), "Part", "overhead_kw",
              y_label="MWh", highlight_max=True)
