"""8 Savings calculator: the user's own "what if", from low and high guesses."""

import streamlit as st

from app.components import kpi_card, status_box
from app.page_utils import co2_range, energy_range, money_range, page_start, settings
from src.savings import LIKELY, UNCERTAIN, savings_range

results = page_start("Savings calculator", "Try your own \"what if\". Enter a low and a high "
                                           "guess for each change and see the range you could "
                                           "save over the period of your data.")
k = results["kpis"]
tariff, ef, currency = settings()

left, right = st.columns(2, gap="large")
with left:
    st.subheader("1. Your site today")
    it_mwh = st.number_input("IT energy (MWh)", min_value=0.0, value=round(k["it_kwh"] / 1000, 1),
                             key="calc_it", help="From your data (measured)")
    pue = st.number_input("PUE", min_value=1.0, value=round(k["pue"], 3), step=0.001,
                          format="%.3f", key="calc_pue", help="From your data (measured)")
    st.subheader("2. What you plan to change")
    st.caption("Cut in overhead (cooling, pumps, UPS losses), % · your guess (assumed)")
    a, b = st.columns(2)
    cut_low = a.number_input("Low %", 0.0, 100.0, 5.0, key="calc_cut_low")
    cut_high = b.number_input("High %", 0.0, 100.0, 15.0, key="calc_cut_high")
    st.caption("Starting values 5–15 % are a cautious guess. See \"How to reduce your cost\" for "
               "the range of each step.")
    st.caption("IT power switched off (unused servers), % · leave at 0 unless an audit found some")
    c, d = st.columns(2)
    off_low = c.number_input("Low % ", 0.0, 100.0, 0.0, key="calc_off_low")
    off_high = d.number_input("High % ", 0.0, 100.0, 0.0, key="calc_off_high")
    cost = st.number_input(f"One-off cost of the changes ({currency}, optional)", min_value=0.0,
                           value=0.0, step=1000.0, key="calc_cost")

out = savings_range(it_mwh * 1000, pue, cut_low, cut_high, off_low, off_high, tariff, ef, cost)
with right:
    st.subheader("Possible saving")
    lo, hi = out["kwh"]
    if out["verdict"] == LIKELY:
        status_box("good", f"A saving is likely if your guesses hold: even the low end saves "
                           f"{energy_range(lo, lo)}.")
    elif out["verdict"] == UNCERTAIN:
        status_box("check", f"Uncertain: the low end is zero. The saving could be anything up to "
                            f"{energy_range(hi, hi)}. Measure after the first change before "
                            "investing more.")
    else:
        status_box("check", "No saving with these values. Enter a cut in overhead or in IT power.")
    kpi_card("Energy", energy_range(*out["kwh"]), "estimate")
    kpi_card("Money", money_range(*out["money"]), "estimate")
    kpi_card("CO₂", co2_range(*out["co2_kg"]), "estimate")
    kpi_card("New PUE", f"{out['new_pue'][0]:.3f} – {out['new_pue'][1]:.3f}", "estimate")
    pay = out["payback_years"]
    if pay:
        longest = "never (low end saves nothing)" if pay[1] is None else f"{pay[1]:.1f} years"
        kpi_card("Payback time", f"{pay[0]:.1f} years – {longest}", "estimate")
    st.caption("How it is calculated: overhead today = IT energy × (PUE − 1). Saving = today's "
               "total − remaining IT × (1 + overhead share after the cut). Switching off IT also "
               "removes the cooling it needed, so the two changes are combined, not added.")
