"""Compare the user's PUE with published global figures (config/benchmarks.toml)."""

import tomllib
from pathlib import Path

import pandas as pd

from src.metrics import complete_rows, compute_kpis

BENCHMARKS_PATH = Path(__file__).resolve().parent.parent / "config" / "benchmarks.toml"
AVERAGE_KEY = "global_average"
LOW_PUE_WARNING = 1.1   # below this, check that every overhead load is in the file
MIN_MONTH_HOURS = 7 * 24  # a month counts towards the monthly range only with a week of data


def load_benchmarks(path: Path = BENCHMARKS_PATH) -> dict[str, dict]:
    """Every reference as ``{key: {name, pue, year, source, link}}``."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def monthly_pue(df: pd.DataFrame) -> pd.Series:
    """PUE of each calendar month (ratio of sums), for months with at least a week of data."""
    rows = complete_rows(df)
    if rows.empty:
        return pd.Series(dtype=float)
    month = rows["ts"].dt.to_period("M")
    sums = rows.groupby(month).agg(total=("total_kw", "sum"), it=("it_kw", "sum"),
                                   hours=("it_kw", "size"))
    sums = sums[(sums["hours"] >= MIN_MONTH_HOURS) & (sums["it"] > 0)]
    return sums["total"] / sums["it"]


def benchmark_pue(df: pd.DataFrame, tariff: float) -> dict:
    """The user's PUE against published figures, and what the difference means.

    Returns ``pue``, ``month_min``, ``month_max`` (None without a full week in any
    month), ``references`` (DataFrame: name, source, year, link, pue,
    overhead_per_100, overhead_for_you_kwh), ``avoided_kwh`` and
    ``avoided_money`` versus the global average (negative = more overhead than
    average), and ``low_pue_warning``.
    """
    kpis = compute_kpis(df, tariff=tariff, emission_factor=0)
    pue, it_kwh = kpis["pue"], kpis["it_kwh"]
    if pue is None:
        raise ValueError("No hours with both IT and total power, so PUE cannot be calculated.")
    months = monthly_pue(df)

    refs = load_benchmarks()
    rows = [{"name": "Your site", "source": "Your uploaded file", "year": None, "link": None,
             "pue": pue}]
    rows += [{k: ref[k] for k in ("name", "source", "year", "link", "pue")} for ref in refs.values()]
    table = pd.DataFrame(rows)
    table["overhead_per_100"] = (table["pue"] - 1) * 100
    table["overhead_for_you_kwh"] = (table["pue"] - 1) * it_kwh

    avoided = (refs[AVERAGE_KEY]["pue"] - pue) * it_kwh
    return {
        "pue": pue,
        "month_min": float(months.min()) if len(months) else None,
        "month_max": float(months.max()) if len(months) else None,
        "references": table,
        "avoided_kwh": avoided,
        "avoided_money": avoided * tariff,
        "low_pue_warning": pue < LOW_PUE_WARNING,
    }
