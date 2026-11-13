"""Run the whole analysis in steps, reporting progress to the Analysing screen.

``run_analysis()`` returns the ``results`` dict used by every analysis page and
by the exports (same keys as ``src.export.collect_results``), plus
``weather_source`` and the table with weather added.
"""

from collections.abc import Callable

import pandas as pd

from src.anomalies import best_predictions, flag_anomalies
from src.benchmark import benchmark_pue
from src.export import monthly_table
from src.location import (
    LocationError,
    fetch_weather,
    find_country,
    free_cooling_hours,
    get_location,
    merge_weather,
)
from src.metrics import compute_kpis
from src.models import train_models
from src.quality import quality_report
from src.recommend import overhead_split, recommend

STEPS = [
    "Reading your file",
    "Cleaning your data",
    "Fetching past weather for your city",
    "Grid CO₂ for your country",
    "Working out efficiency and costs",
    "Training forecasts",
    "Finding waste",
    "Preparing your steps to cut cost",
]
FACTS = [
    "The global average PUE is 1.52: for every 1 kWh used by servers, about 0.5 kWh goes to "
    "cooling, power losses and lighting (Uptime Institute 2026).",
    "Raising the cooling setpoint by 1 °C can cut cooling energy by 2-4 % within the "
    "recommended 18-27 °C range.",
    "A pump or fan running 10 % slower can use about 27 % less energy (affinity law).",
    "Studies estimate 15-30 % of servers in sites without regular checks do no useful work.",
    "Water-side free cooling suits climates with 3,000 or more hours a year below 12.8 °C "
    "wet-bulb.",
]

Report = Callable[[int, str, str], None]  # (step index, "running" | "done" | "warning", detail)


def _no_report(step: int, status: str, detail: str) -> None:
    pass


def run_analysis(data: pd.DataFrame, answers: dict, upload_report: dict | None = None,
                 file_name: str | None = None, report: Report = _no_report) -> dict:
    """Run every step on the user's clean hourly table and their answers."""
    upload_report = upload_report or {}
    tariff = float(answers["price"])

    report(0, "running", "")
    hours = len(data)
    report(0, "done", f"{hours:,} hours from {file_name or 'your file'}")

    report(1, "running", "")
    faulty = upload_report.get("faulty_readings", 0) + upload_report.get("rows_bad_time", 0)
    report(1, "done", f"{faulty:,} faulty readings removed, "
                      f"{upload_report.get('missing_hours', 0):,} gaps left empty")

    country = find_country(answers["country"])
    location = {"country": country["country"], "currency": country["currency"],
                "emission_factor": float(country["emission_factor"])
                if country["emission_factor"] else None,
                "ef_source": country["ef_source"] or None}

    report(2, "running", "")
    df, weather_source = merge_weather(data, None)
    if weather_source == "file":
        report(2, "done", "Your file has outdoor temperature and humidity, so we use those")
        weather = df
    else:
        try:
            place = get_location(answers["country"], answers["city"])
            location.update(lat=place["lat"], lon=place["lon"], city=place["city"])
            fetched = fetch_weather(place["lat"], place["lon"], data["ts"].min(),
                                    data["ts"].max())
            df, weather_source = merge_weather(data, fetched)
            weather = fetched
            report(2, "done", f"{len(fetched):,} hours of past weather for {place['city']} "
                              "(Open-Meteo)")
        except LocationError as err:
            weather = df
            report(2, "warning", f"{err} Weather-based results are left out.")
    location["weather_source"] = weather_source
    location["free_cooling_hours"] = (free_cooling_hours(weather)
                                      if {"temp_c", "humidity"} <= set(weather.columns) else None)

    report(3, "running", "")
    ef = location["emission_factor"]
    if ef is None:
        report(3, "warning", f"No grid CO₂ factor is known for {country['country']}; CO₂ results "
                             "are left out.")
    else:
        report(3, "done", f"{ef:.3f} kg CO₂ per kWh ({location['ef_source']})")

    report(4, "running", "")
    kpis = compute_kpis(df, tariff=tariff, emission_factor=ef or 0.0)
    benchmark = benchmark_pue(df, tariff)
    report(4, "done", f"PUE {kpis['pue']:.3f} (global average 1.52)")

    report(5, "running", "")
    target = "mechanical_kw" if "mechanical_kw" in df and df["mechanical_kw"].notna().any() \
        else "total_kw"
    try:
        forecast = train_models(df, target=target)
        best = forecast["metrics"].iloc[0]
        report(5, "done", f"Best model: {best['model'].replace('_', ' ')}, off by "
                          f"{best['mae']:.1f} kW on average")
    except ValueError as err:
        forecast = None
        report(5, "warning", str(err))

    report(6, "running", "")
    if forecast is not None:
        anomalies = flag_anomalies(df, best_predictions(forecast), tariff, target=target)
        n = len(anomalies)
        report(6, "done", f"{n} period{'' if n == 1 else 's'} used more energy than expected")
    else:
        anomalies = pd.DataFrame()
        report(6, "warning", "Skipped: no forecast to compare with")

    report(7, "running", "")
    steps = recommend(df, kpis, answers, location)
    report(7, "done", f"{len(steps['steps'])} steps fit your site")

    ts = df["ts"].dropna()
    return {
        "file_name": file_name,
        "period": f"{ts.min():%d %b %Y} – {ts.max():%d %b %Y} · {hours:,} hours",
        "currency": answers.get("currency", ""),
        "tariff": tariff,
        "kpis": kpis,
        "quality": quality_report(df),
        "monthly": monthly_table(df, tariff),
        "anomalies": anomalies,
        "steps": steps,
        "forecast": forecast,
        "forecast_target": target,
        "benchmark": benchmark,
        "overhead": overhead_split(df),
        "answers": answers,
        "location": location,
        "weather_source": weather_source,
        "table": df,
    }
