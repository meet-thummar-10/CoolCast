"""Shared helpers for the 11 analysis pages.

Every page starts with ``results = page_start(title, lead)``. It stops the page
with a friendly message when there are no results yet, and returns the
results with money and CO2 recalculated for the price and grid factor
currently set in the sidebar.
"""

import copy

import pandas as pd
import streamlit as st

from app.components import empty_state
from app.formatting import fmt_co2, fmt_energy, fmt_money, fmt_range
from app.state import go_to
from src.metrics import compute_kpis


def settings() -> tuple[float, float, str]:
    """Electricity price, grid CO2 factor and currency, as currently set in the sidebar."""
    s = st.session_state
    answers = s.get("answers") or {}
    tariff = s.get("tariff") or answers.get("price") or 0.0
    ef = s.get("emission_factor")
    if ef is None:
        ef = answers.get("emission_factor") or 0.0
    return float(tariff), float(ef), answers.get("currency") or "USD"


def current_results() -> dict | None:
    """The analysis results with every money and CO2 figure using the current settings."""
    results = st.session_state.get("results") or {}
    data = st.session_state.get("data")
    if not results.get("kpis") or data is None:
        return None
    tariff, ef, currency = settings()
    out = copy.copy(results)
    out["tariff"], out["currency"] = tariff, currency
    out["kpis"] = compute_kpis(data, tariff=tariff, emission_factor=ef)
    out["monthly"] = results["monthly"].assign(cost=results["monthly"]["total_kwh"] * tariff)
    anomalies = results.get("anomalies")
    if anomalies is not None and len(anomalies):
        out["anomalies"] = anomalies.assign(excess_cost=anomalies["excess_kwh"] * tariff)
    bench = dict(results["benchmark"])
    bench["avoided_money"] = bench["avoided_kwh"] * tariff
    out["benchmark"] = bench
    steps = copy.deepcopy(results["steps"])
    for step in steps["steps"]:
        if step["low_kwh"] is not None:
            step["low_money"], step["high_money"] = step["low_kwh"] * tariff, \
                step["high_kwh"] * tariff
            step["low_co2_kg"], step["high_co2_kg"] = step["low_kwh"] * ef, \
                step["high_kwh"] * ef
    out["steps"] = steps
    out["location"] = {**results.get("location", {}), "emission_factor": ef}
    return out


def page_start(title: str, lead: str) -> dict:
    """Title and one-line explanation, then the current results (or a message and stop)."""
    st.title(title)
    st.caption(lead)
    results = current_results()
    if results is None:
        empty_state("There is no analysis yet. Upload your data and answer the questions first.")
        st.button("Go to upload", key="no_results_upload", on_click=go_to, args=("upload",))
        st.stop()
    return results


def table() -> pd.DataFrame:
    """The user's clean hourly table (with weather added when it was fetched)."""
    return st.session_state["data"]


def has(df: pd.DataFrame, *columns: str) -> bool:
    """Whether the table has data in every one of these columns."""
    return all(c in df and df[c].notna().any() for c in columns)


def money(amount) -> str:
    return fmt_money(amount, settings()[2])


def money_range(low, high) -> str:
    return fmt_range(low, high, fmt_money, settings()[2])


def energy_range(low, high) -> str:
    return fmt_range(low, high, fmt_energy)


def co2_range(low, high) -> str:
    return fmt_range(low, high, fmt_co2)
