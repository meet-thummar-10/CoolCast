"""9 Benchmark: the user's PUE against published global figures."""

import plotly.graph_objects as go
import streamlit as st

from app.components import FONT, HIGHLIGHT, INK, PRIMARY, kpi_card, status_box
from app.formatting import fmt_energy
from app.page_utils import money, page_start

results = page_start("Benchmark", "How your PUE compares with published global figures. Lower is "
                                  "better: 1.0 would mean every unit of power goes to the servers.")
b = results["benchmark"]
refs = b["references"]
months = (f"{b['month_min']:.3f} – {b['month_max']:.3f}" if b["month_min"] is not None else "–")
average = refs.loc[refs["name"] == "Global average", "pue"].iloc[0]

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)
with c1:
    kpi_card("Your PUE", f"{b['pue']:.3f}", "measured")
with c2:
    kpi_card("Your monthly range", months, "measured")
with c3:
    kpi_card("Global average", f"{average:.2f}", "assumed", help="Uptime Institute 2026 survey")
with c4:
    avoided = b["avoided_kwh"]
    kpi_card("Energy avoided vs average" if avoided >= 0 else "Extra energy vs average",
             f"≈ {fmt_energy(abs(avoided))}", "estimate",
             help=f"≈ {money(abs(b['avoided_money']))} at your price")

colors = [PRIMARY if n == "Your site" else "#CBD5E1" for n in refs["name"]]
fig = go.Figure(go.Bar(x=refs["pue"] - 1, y=refs["name"], base=1, orientation="h",
                       marker_color=colors, text=[f"{p:.3f}" if n == "Your site" else f"{p:.2f}"
                                                  for n, p in zip(refs["name"], refs["pue"])],
                       textposition="outside"))
if b["month_min"] is not None:
    fig.add_shape(type="line", x0=b["month_min"], x1=b["month_max"], y0=0, y1=0,
                  line=dict(color=HIGHLIGHT, width=6))
fig.update_layout(title="PUE comparison (thick line on your bar = your monthly range)",
                  font=dict(family=FONT, color=INK), xaxis=dict(range=[1, 1.7], title="PUE"),
                  yaxis=dict(autorange="reversed"), plot_bgcolor="#FFFFFF", height=320,
                  margin=dict(l=10, r=10, t=60, b=10))
st.plotly_chart(fig)

st.subheader("What the difference means")
table = refs.assign(
    pue=refs["pue"].round(3),
    overhead_per_100=refs["overhead_per_100"].round(0).astype(int).astype(str) + " kWh",
    overhead_for_you=refs["overhead_for_you_kwh"].map(fmt_energy))
st.dataframe(table[["name", "pue", "overhead_per_100", "overhead_for_you", "source"]].rename(
    columns={"name": "Site", "pue": "PUE", "overhead_per_100": "Overhead per 100 kWh of IT",
             "overhead_for_you": "Overhead for your IT energy", "source": "Source"}),
    hide_index=True)

if b["low_pue_warning"]:
    status_box("check", f"Your PUE is unusually low ({b['pue']:.3f}, below Google's fleet "
                        "average). Before relying on it, check that every overhead load is in "
                        "your file: cooling, pumps, UPS and transformer losses, lighting.")
st.info("**Comparing fairly:** PUE depends on climate, site size and where meters are placed. "
        "Regional or country averages are not shown because they could not be verified from an "
        "official source.", icon=":material/info:")
