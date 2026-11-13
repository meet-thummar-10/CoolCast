"""Export the whole analysis: an Excel workbook and a structured PDF report.

The user's data is deleted when they exit, so these files are how they keep
their results. Every number keeps its label (measured / modelled / assumed /
estimate), money is in the user's currency, and savings are always ranges
that are never added together.

``collect_results()`` runs the analysis and returns the ``results`` dict that
``build_excel()`` and ``build_pdf()`` take. Keys: ``file_name, period,
currency, tariff, kpis, quality, monthly, anomalies, steps, forecast,
benchmark, overhead, answers, location``.
"""

import io
import math
import re
from datetime import date

import pandas as pd
from fpdf import FPDF

from src.anomalies import best_predictions, flag_anomalies
from src.benchmark import benchmark_pue
from src.metrics import complete_rows, compute_kpis, interval_hours
from src.models import train_models
from src.quality import quality_report
from src.recommend import OPTIONS, overhead_split, recommend

SHEETS = ["Summary", "Monthly", "Anomalies", "Steps to reduce cost", "Forecast",
          "Your answers and settings", "Data quality"]
NOT_ADDED = "Savings are estimates shown as ranges. Do not add the ranges together."
QUESTIONS = {
    "country": "Country", "city": "City", "price": "Electricity price per kWh (your bill)",
    "currency": "Currency", "site_type": "Type of data centre",
    "cooling_system": "Main cooling system", "free_cooling": "Free cooling already used",
    "supply_temp_c": "Supply temperature to the servers (°C)",
    "vfd": "Variable-speed drives on pumps and fans", "ups_mode": "How the UPS units run",
    "unused_servers": "Unused servers found and removed", "can_change": "Changes you can make",
}


# ---------------------------------------------------------------- collecting


def monthly_table(df: pd.DataFrame, tariff: float) -> pd.DataFrame:
    """Energy, PUE and cost per calendar month (ratio of sums)."""
    rows = complete_rows(df)
    hours = interval_hours(df)
    month = rows["ts"].dt.to_period("M").astype(str)
    out = rows.groupby(month).agg(it_kwh=("it_kw", "sum"), total_kwh=("total_kw", "sum"))
    out = out * hours
    out["pue"] = out["total_kwh"] / out["it_kwh"]
    out["cost"] = out["total_kwh"] * tariff
    return out.reset_index(names="month")


def collect_results(df: pd.DataFrame, answers: dict, location: dict | None = None,
                    file_name: str | None = None) -> dict:
    """Run every analysis on the standard hourly table and gather the results.

    ``answers`` uses the Questions screen's codes (see ``src.recommend.OPTIONS``)
    and must include ``price`` and ``currency``. ``location`` may give
    ``emission_factor`` and ``free_cooling_hours``.
    """
    location = location or {}
    tariff = float(answers["price"])
    ef = location.get("emission_factor") or 0.0
    kpis = compute_kpis(df, tariff=tariff, emission_factor=ef)

    target = "mechanical_kw" if "mechanical_kw" in df and df["mechanical_kw"].notna().any() \
        else "total_kw"
    try:
        forecast = train_models(df, target=target)
        anomalies = flag_anomalies(df, best_predictions(forecast), tariff, target=target)
    except ValueError:  # not enough data to train
        forecast, anomalies = None, pd.DataFrame()
    ts = df["ts"].dropna()
    return {
        "file_name": file_name,
        "period": f"{ts.min():%d %b %Y} - {ts.max():%d %b %Y}" if len(ts) else "",
        "currency": answers.get("currency", ""),
        "tariff": tariff,
        "kpis": kpis,
        "quality": quality_report(df),
        "monthly": monthly_table(df, tariff),
        "anomalies": anomalies,
        "steps": recommend(df, kpis, answers, location),
        "forecast": forecast,
        "forecast_target": target,
        "benchmark": benchmark_pue(df, tariff),
        "overhead": overhead_split(df),
        "answers": answers,
        "location": location,
    }


# ---------------------------------------------------------------- formatting


def _sig(x: float, digits: int = 2) -> float:
    if not x:
        return 0
    return round(x, digits - 1 - math.floor(math.log10(abs(x))))


def _num(x: float) -> str:
    text = f"{x:,.2f}".rstrip("0").rstrip(".") if abs(x) < 100 else f"{x:,.0f}"
    return text


def fmt_energy(kwh: float) -> str:
    for size, unit in ((1e6, "GWh"), (1e3, "MWh")):
        if abs(kwh) >= size:
            return f"{_num(kwh / size)} {unit}"
    return f"{_num(kwh)} kWh"


def fmt_money(amount: float, currency: str) -> str:
    """Money with the ISO code: "INR 4.4 lakh", "USD 12,500", "EUR 3.4 million"."""
    steps = ([(1e7, " crore"), (1e5, " lakh")] if currency == "INR"
             else [(1e9, " billion"), (1e6, " million")])
    for size, word in steps:
        if abs(amount) >= size:
            return f"{currency} {_num(amount / size)}{word}"
    return f"{currency} {amount:,.0f}"


def fmt_co2(kg: float) -> str:
    return f"{_num(kg / 1000)} t CO2" if abs(kg) >= 1000 else f"{_num(kg)} kg CO2"


_PARTS = re.compile(r"^(-?\D*?)(\d[\d,]*(?:\.\d+)?)(.*)$")


def fmt_range(low: float, high: float, fmt, *args) -> str:
    """Both ends rounded to 2 significant figures, sharing the unit: "55 - 110 MWh",
    "INR 4.4 - 8.8 lakh", "INR 0 - 8.5 lakh"."""
    lo_text, hi_text = fmt(_sig(low), *args), fmt(_sig(high), *args)
    if lo_text == hi_text:
        return hi_text
    lo, hi = _PARTS.match(lo_text), _PARTS.match(hi_text)
    if lo and hi:
        if _sig(low) == 0:
            return f"{hi.group(1)}0 - {hi.group(2)}{hi.group(3)}"
        if lo.group(1) == hi.group(1) and lo.group(3) == hi.group(3):
            return f"{hi.group(1)}{lo.group(2)} - {hi.group(2)}{hi.group(3)}"
    return f"{lo_text} - {hi_text}"


def _answer_text(key: str, value) -> str:
    if value is None or value == "":
        return "I don't know"
    return OPTIONS.get(key, {}).get(value, str(value))


# ---------------------------------------------------------------- Excel


def _sheets(results: dict) -> dict[str, pd.DataFrame]:
    k, q, cur = results["kpis"], results["quality"], results["currency"]
    bench = results["benchmark"]
    summary = pd.DataFrame([
        ("PUE", k["pue"], "ratio", "measured"),
        ("Total energy", k["total_kwh"], "kWh", "measured"),
        ("IT energy", k["it_kwh"], "kWh", "measured"),
        ("Overhead energy", k["total_kwh"] - k["it_kwh"], "kWh", "measured"),
        ("Cooling share", k["cooling_share"], "fraction", "measured"),
        ("Electricity cost", k["cost"], cur, "assumed"),
        ("CO2 emitted", k["co2_kg"], "kg CO2", "assumed"),
        ("CUE", k["cue"], "kg CO2 per kWh of IT", "assumed"),
        ("Global average PUE", 1.52, "ratio", "assumed"),
        ("Energy avoided vs global average", bench["avoided_kwh"], "kWh", "modelled"),
        ("Data quality grade", q["grade"], "", "measured"),
        ("Note", NOT_ADDED, "", "estimate"),
    ], columns=["metric", "value", "unit", "label"])

    monthly = results["monthly"].assign(label="measured")
    anomalies = results["anomalies"]
    anomalies = (anomalies.assign(label="modelled") if len(anomalies)
                 else pd.DataFrame(columns=["start", "end", "hours", "excess_kwh", "excess_cost",
                                            "label"]))

    step_cols = ["title", "effort", "confidence", "found", "todo", "low_kwh", "high_kwh",
                 "low_money", "high_money", "low_co2_kg", "high_co2_kg", "per", "calc",
                 "warning", "sources", "label"]
    steps = pd.DataFrame(results["steps"]["steps"], columns=step_cols)

    fc = results["forecast"]
    if fc is not None:
        forecast = fc["metrics"].assign(best=lambda m: m["model"] == fc["best"],
                                        target=results.get("forecast_target"), label="modelled")
    else:
        forecast = pd.DataFrame(columns=["model", "mae", "rmse", "r2", "best", "target", "label"])

    answers = [(QUESTIONS.get(key, key), _answer_text(key, value), "assumed")
               for key, value in results["answers"].items()]
    loc = results["location"]
    for key, name in (("emission_factor", "Grid CO2 factor (kg CO2/kWh)"),
                      ("ef_source", "Grid CO2 source"),
                      ("free_cooling_hours", "Free-cooling hours per year"),
                      ("weather_source", "Weather from")):
        if loc.get(key) is not None:
            answers.append((name, loc[key], "assumed"))
    settings = pd.DataFrame(answers, columns=["question", "answer", "label"])

    quality = pd.DataFrame([
        ("Completeness", q["completeness"], "measured"),
        ("Missing hours", q["missing_hours"], "measured"),
        ("Longest gap (hours)", q["longest_gap_h"], "measured"),
        ("Grade", q["grade"], "measured"),
    ], columns=["metric", "value", "label"])

    return dict(zip(SHEETS, [summary, monthly, anomalies, steps, forecast, settings, quality]))


def build_excel(results: dict) -> bytes:
    """An .xlsx workbook with one sheet per analysis; every sheet has a ``label`` column."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, table in _sheets(results).items():
            table.to_excel(writer, sheet_name=name, index=False)
            sheet = writer.sheets[name]
            for column in sheet.columns:
                longest = max(len(str(c.value)) if c.value is not None else 0 for c in column)
                sheet.column_dimensions[column[0].column_letter].width = min(max(10, longest + 2),
                                                                             60)
    return buffer.getvalue()


# ---------------------------------------------------------------- PDF

LATIN = {"–": "-", "—": "-", "≈": "~", "≥": ">=", "≤": "<=", "₂": "2", "’": "'", "‘": "'",
         "“": '"', "”": '"', "→": "->", "…": "...", "₹": "INR ", "€": "EUR ", "£": "GBP "}
INK, PRIMARY, HIGHLIGHT, GREY = (15, 23, 42), (8, 145, 178), (67, 56, 202), (100, 116, 139)


def _latin(text) -> str:
    """The PDF's built-in fonts only cover Latin-1, so swap the few symbols we use."""
    text = str(text)
    for old, new in LATIN.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("helvetica", size=8)
        self.set_text_color(*GREY)
        self.cell(0, 6, f"CoolCast report - page {self.page_no()}/{{nb}}", align="C")

    def h1(self, text: str) -> None:
        self.set_font("helvetica", "B", 16)
        self.set_text_color(*INK)
        self.ln(2)
        self.multi_cell(0, 9, _latin(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def h2(self, text: str) -> None:
        self.set_font("helvetica", "B", 12)
        self.set_text_color(*INK)
        self.multi_cell(0, 7, _latin(text), new_x="LMARGIN", new_y="NEXT")

    def para(self, text: str, size: int = 10, color=INK, style: str = "") -> None:
        self.set_font("helvetica", style, size)
        self.set_text_color(*color)
        self.multi_cell(0, 5, _latin(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def table(self, header: list[str], rows: list[list], widths: list[float]) -> None:
        self.set_font("helvetica", "B", 9)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(*INK)
        for text, w in zip(header, widths):
            self.cell(w, 7, _latin(text), border=1, fill=True)
        self.ln()
        self.set_font("helvetica", size=9)
        for row in rows:
            for text, w in zip(row, widths):
                self.cell(w, 6, _latin(text), border=1)
            self.ln()
        self.ln(3)

    def bars(self, labels: list[str], values: list[float], unit: str, start: float = 0) -> None:
        """A simple horizontal bar chart; the largest bar is highlighted."""
        top = max(values) if values else 1
        width = 120
        self.set_font("helvetica", size=8)
        for label, value in zip(labels, values):
            share = (value - start) / (top - start) if top > start else 0
            self.set_text_color(*INK)
            self.cell(40, 6, _latin(label))
            self.set_fill_color(*(HIGHLIGHT if value == top else PRIMARY))
            self.cell(max(share * width, 0.5), 5, "", fill=True)
            self.cell(2, 5, "")
            self.cell(30, 5, _latin(f"{_num(value)} {unit}"))
            self.ln(6)
        self.ln(2)


def build_pdf(results: dict) -> bytes:
    """A structured PDF report of the whole analysis."""
    k, cur, q = results["kpis"], results["currency"], results["quality"]
    pdf = _Report()
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_title("CoolCast report")
    pdf.add_page()

    # Cover and key numbers
    pdf.set_font("helvetica", "B", 22)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 12, "CoolCast report", new_x="LMARGIN", new_y="NEXT")
    loc = results["location"]
    place = ", ".join(str(results["answers"].get(x)) for x in ("city", "country")
                      if results["answers"].get(x))
    pdf.para(f"File: {results.get('file_name') or '-'}   |   Period: {results['period']}   |   "
             f"Location: {place or '-'}   |   Created: {date.today():%d %b %Y}", 9, GREY)
    pdf.h1("Key numbers")
    pdf.table(["Number", "Value", "Label"], [
        ["PUE (lower is better)", f"{k['pue']:.3f}", "measured"],
        ["Total energy", fmt_energy(k["total_kwh"]), "measured"],
        ["IT energy", fmt_energy(k["it_kwh"]), "measured"],
        ["Overhead energy", fmt_energy(k["total_kwh"] - k["it_kwh"]), "measured"],
        ["Electricity cost", fmt_money(k["cost"], cur), "assumed (your price)"],
        ["CO2 emitted", fmt_co2(k["co2_kg"]), "assumed (grid factor)"],
        ["Data quality grade", f"{q['grade']} ({q['completeness']:.0%} complete)", "measured"],
    ], [70, 60, 50])
    split = results.get("overhead")
    if split:
        weather = (f", follows the weather {split['follows_weather']:.0%}"
                   if split["follows_weather"] is not None else "")
        pdf.para(f"Overhead: always on {split['always_on']:.0%}, follows the servers "
                 f"{split['follows_servers']:.0%}{weather} (fit quality R2 {split['r2']:.2f}).")

    pdf.h2("Energy per month")
    monthly = results["monthly"]
    pdf.bars(monthly["month"].tolist(), (monthly["total_kwh"] / 1000).round(1).tolist(), "MWh")

    # Steps
    pdf.add_page()
    pdf.h1("How to reduce your cost")
    pdf.para(NOT_ADDED + " The low end can be 0 if equipment is already optimised. Confirm any "
             "change with your engineer or supplier before acting.", 9, HIGHLIGHT, "B")
    for n, s in enumerate(results["steps"]["steps"], 1):
        pdf.h2(f"{n}. {s['title']}")
        pdf.para(f"Effort: {s['effort']}   |   Confidence: {s['confidence']}   |   Estimate", 8,
                 GREY)
        pdf.para(f"What we found: {s['found']}", 9)
        pdf.para(f"What to do: {s['todo']}", 9)
        if s["low_kwh"] is not None:
            per = f" per {s['per']}" if s["per"] else ""
            saving = (f"Possible saving{per}: {fmt_range(s['low_kwh'], s['high_kwh'], fmt_energy)}"
                      f"  |  {fmt_range(s['low_money'], s['high_money'], fmt_money, cur)}")
            if s["low_co2_kg"] is not None:
                saving += f"  |  {fmt_range(s['low_co2_kg'], s['high_co2_kg'], fmt_co2)}"
            pdf.para(saving, 10, PRIMARY, "B")
        pdf.para(f"How it is calculated: {s['calc']}", 8, GREY)
        pdf.para(f"Before you act: {s['warning']}", 9, (154, 52, 18))
        pdf.para(f"Sources: {s['sources']}", 8, GREY)
    for s in results["steps"]["skipped"]:
        pdf.para(f"Not shown ({s['id']}): {s['reason']}", 8, GREY)

    # Benchmark
    pdf.add_page()
    pdf.h1("Benchmark")
    bench = results["benchmark"]
    refs = bench["references"]
    pdf.bars(refs["name"].tolist(), refs["pue"].round(3).tolist(), "PUE", start=1.0)
    month_range = (f"{bench['month_min']:.3f} - {bench['month_max']:.3f}"
                   if bench["month_min"] is not None else "-")
    pdf.para(f"Your PUE {bench['pue']:.3f} (monthly range {month_range}). Energy avoided compared "
             f"with the global average: {fmt_energy(bench['avoided_kwh'])} "
             f"({fmt_money(bench['avoided_money'], cur)}).")
    if bench["low_pue_warning"]:
        pdf.para("Your PUE is unusually low. Check that every overhead load (cooling, pumps, UPS "
                 "and transformer losses, lighting) is in your file.", 9, (154, 52, 18))
    pdf.table(["Site", "PUE", "Year", "Source"],
              [[r["name"], f"{r['pue']:.3f}", "" if pd.isna(r["year"]) else int(r["year"]),
                str(r["source"])[:60]]
               for _, r in refs.iterrows()], [40, 18, 14, 118])

    # Anomalies and forecast
    pdf.h1("Anomalies")
    anomalies = results["anomalies"]
    if len(anomalies):
        pdf.para("Periods that used more energy than the forecast expected. Worth investigating, "
                 "not proof of a fault.", 9)
        pdf.table(["Start", "End", "Hours", "Extra energy", "Extra cost"],
                  [[f"{r['start']:%d %b %Y %H:%M}", f"{r['end']:%d %b %Y %H:%M}", r["hours"],
                    fmt_energy(r["excess_kwh"]), fmt_money(r["excess_cost"], cur)]
                   for _, r in anomalies.head(10).iterrows()], [42, 42, 16, 40, 50])
    else:
        pdf.para("No periods were flagged.", 9)
    pdf.h1("Forecast accuracy")
    fc = results["forecast"]
    if fc is not None:
        pdf.table(["Model", "MAE (kW)", "RMSE (kW)", "R2", "Best"],
                  [[r["model"], f"{r['mae']:.2f}", f"{r['rmse']:.2f}", f"{r['r2']:.2f}",
                    "yes" if r["model"] == fc["best"] else ""]
                   for _, r in fc["metrics"].iterrows()], [50, 30, 30, 30, 20])
    else:
        pdf.para("Not enough data to train a forecast.", 9)

    # Answers, quality and method
    pdf.add_page()
    pdf.h1("Your answers and settings")
    rows = [[QUESTIONS.get(key, key), _answer_text(key, v)] for key, v in results["answers"].items()]
    if loc.get("emission_factor") is not None:
        rows.append(["Grid CO2 factor", f"{loc['emission_factor']} kg CO2/kWh "
                                         f"({loc.get('ef_source') or 'assumed'})"[:70]])
    pdf.table(["Question", "Answer"], [[a, str(b)[:70]] for a, b in rows], [70, 120])
    pdf.h1("Data quality")
    pdf.para(f"Grade {q['grade']}: {q['completeness']:.1%} of hours complete, "
             f"{q['missing_hours']} missing hours, longest gap {q['longest_gap_h']} hours.", 9)
    pdf.h1("Method and limitations")
    pdf.para("PUE is total energy divided by IT energy over the whole period (a ratio of sums). "
             "Every number is labelled measured (from your file), modelled (from a model on your "
             "data) or assumed (from your answers or a published source). Savings are for the "
             "period covered by your data and come from published studies; real savings depend "
             "on your building and need an engineer's assessment. CoolCast analyses recorded "
             "data and does not control any equipment.", 9)
    return bytes(pdf.output())
