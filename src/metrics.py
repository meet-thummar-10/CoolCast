"""Headline efficiency metrics: PUE, energy, cooling share, cost, CO2 and CUE.

Rules (docs/contracts.md):
- energy (kWh) = power (kW) x interval (hours)
- PUE = total kWh / IT kWh, a ratio of sums, never an average of hourly PUE
"""

import pandas as pd

from src.clean import COMPONENTS, MECHANICAL

N_LOAD_BINS = 10


def interval_hours(df: pd.DataFrame) -> float:
    """Time step of the table in hours (most common gap between rows); 1 if unknown."""
    if "ts" not in df or len(df) < 2:
        return 1.0
    step = df["ts"].sort_values().diff().dropna().mode()
    return step.iloc[0].total_seconds() / 3600 if len(step) else 1.0


def complete_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where all five power components have a value."""
    return df.dropna(subset=COMPONENTS)


def compute_kpis(df: pd.DataFrame, tariff: float, emission_factor: float) -> dict:
    """Energy, efficiency, cost and CO2 for the rows in ``df``.

    ``tariff`` is in ₹/kWh and ``emission_factor`` in kg CO2/kWh.
    Rows with any missing power value are skipped.

    Returns ``{pue, it_kwh, total_kwh, cooling_share, cost, co2_kg, cue}``.
    Ratios are None when there is no IT energy to divide by.
    """
    rows = complete_rows(df)
    hours = interval_hours(df)
    it_kwh = float(rows["it_kw"].sum() * hours)
    total_kwh = float(rows[COMPONENTS].sum(axis=1).sum() * hours)
    mechanical_kwh = float(rows[MECHANICAL].sum(axis=1).sum() * hours)
    co2_kg = total_kwh * emission_factor

    return {
        "pue": total_kwh / it_kwh if it_kwh else None,
        "it_kwh": it_kwh,
        "total_kwh": total_kwh,
        "cooling_share": mechanical_kwh / total_kwh if total_kwh else None,
        "cost": total_kwh * tariff,
        "co2_kg": co2_kg,
        "cue": co2_kg / it_kwh if it_kwh else None,
    }


def pue_by_load(df: pd.DataFrame, bins: int = N_LOAD_BINS) -> pd.DataFrame:
    """PUE (ratio of sums) for equal-width bins of IT load.

    Returns columns ``load_bin`` (label such as "1,000-1,300 kW"),
    ``it_kw_mid`` (bin centre, for plotting), ``pue`` and ``hours``.
    Empty bins are left out.
    """
    rows = complete_rows(df)
    columns = ["load_bin", "it_kw_mid", "pue", "hours"]
    if rows.empty:
        return pd.DataFrame(columns=columns)

    total = rows[COMPONENTS].sum(axis=1)
    groups = pd.cut(rows["it_kw"], bins=bins, include_lowest=True)
    sums = pd.DataFrame({"total": total, "it": rows["it_kw"], "bin": groups})
    agg = sums.groupby("bin", observed=True).agg(total=("total", "sum"), it=("it", "sum"),
                                                 hours=("it", "size"))
    out = pd.DataFrame({
        "load_bin": [f"{iv.left:,.0f}-{iv.right:,.0f} kW" for iv in agg.index],
        "it_kw_mid": [iv.mid for iv in agg.index],
        "pue": (agg["total"] / agg["it"]).to_numpy(),
        "hours": agg["hours"].to_numpy(),
    })
    return out[columns]
