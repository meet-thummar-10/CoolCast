"""Turn any data centre's CSV or Excel file into CoolCast's standard hourly table.

Steps: ``read_file`` -> ``suggest_mapping`` (the user confirms) ->
``apply_mapping`` (rename, convert units, clean, resample hourly) ->
``check_length``.

Standard columns: ts, it_kw, total_kw and, when the file has them,
cooling_kw, pump_kw, hvac_kw, plug_kw, other_kw, mechanical_kw, temp_c,
humidity. Missing readings stay empty; they are never filled with 0.
"""

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.clean import PUE_RANGE
from src.data import load_demo_data

MAX_BYTES = 200 * 1024 * 1024
REQUIRED = ("ts", "it_kw")
PARTS = ("cooling_kw", "pump_kw", "hvac_kw", "plug_kw", "other_kw")
MECHANICAL = ("cooling_kw", "pump_kw", "hvac_kw")
POWER = ("it_kw", "total_kw", *PARTS)
STANDARD = ("ts", "it_kw", "total_kw", *PARTS, "temp_c", "humidity")
OUTPUT_ORDER = ("ts", "it_kw", "total_kw", *PARTS, "mechanical_kw", "temp_c", "humidity")

# Column names in our template, and the standard name each one becomes.
TEMPLATE = {
    "timestamp": "ts", "it_kw": "it_kw", "total_kw": "total_kw", "cooling_kw": "cooling_kw",
    "pump_kw": "pump_kw", "hvac_kw": "hvac_kw", "plug_kw": "plug_kw", "other_kw": "other_kw",
    "temp_c": "temp_c", "humidity_pct": "humidity",
}

# Words that suggest each standard column (checked on the lower-case name).
KEYWORDS = {
    "ts": [r"\btime", r"\bdate", r"\bts\b", r"timestamp", r"datetime", r"\bperiod\b"],
    "it_kw": [r"\bit\b", r"\bit[_ ]?(load|power|kw|w)\b", r"\bserver", r"\bcritical",
              r"\bups output", r"\bups out\b"],
    "total_kw": [r"\btotal", r"\bfacility", r"\bsite\b", r"main meter", r"\bbuilding",
                 r"\butility", r"\bincomer"],
    "cooling_kw": [r"\bchiller", r"\bcooling", r"\btower", r"\bcooler", r"\bcondenser"],
    "pump_kw": [r"\bpump"],
    "hvac_kw": [r"\bhvac", r"\bcrah", r"\bcrac", r"\bahu\b", r"air handl", r"\bfan"],
    "plug_kw": [r"\blight", r"\bplug"],
    "other_kw": [r"\bother", r"\bloss", r"\btransformer", r"\bmisc", r"\boffice", r"security"],
    "temp_c": [r"\btemp", r"\boat\b", r"dry ?bulb", r"outdoor", r"outside air"],
    "humidity": [r"humid", r"\brh\b"],
}
# Earlier entries win when a name matches several (e.g. "cooling pump" is a pump).
PRIORITY = ("ts", "humidity", "temp_c", "pump_kw", "plug_kw", "hvac_kw", "cooling_kw",
            "other_kw", "total_kw", "it_kw")

# (minimum days, level, message). The shortest 1, 6 and 12 calendar months
# are 28, 181 and 365 days, so a full calendar period always qualifies.
LEVELS = (
    (365, "best", "12 months or more: the best results."),
    (181, "good", "6 months or more: good results."),
    (28, "limited", "Less than 6 months: results are less accurate than with 6+ months of data."),
    (0, "blocked", "Less than 1 month of data. Please upload at least 1 month."),
)


class UploadError(ValueError):
    """A problem with the user's file, with a message they can act on."""


# ---------------------------------------------------------------- reading


def read_file(file, name: str | None = None) -> pd.DataFrame:
    """Read a CSV (UTF-8, comma-separated) or Excel .xlsx file (first sheet).

    ``file`` is a path or a file-like object (such as Streamlit's upload).
    Every cell is read as text so nothing is silently converted.
    """
    name = name or getattr(file, "name", None) or str(file)
    data = Path(file).read_bytes() if isinstance(file, (str, Path)) else file.read()
    if len(data) > MAX_BYTES:
        raise UploadError("The file is larger than 200 MB. Please upload a smaller file.")
    suffix = Path(name).suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(io.BytesIO(data), dtype=str, encoding="utf-8-sig",
                             skipinitialspace=True)
        elif suffix == ".xlsx":
            df = pd.read_excel(io.BytesIO(data), sheet_name=0, dtype=str)
        else:
            raise UploadError("Please upload a CSV (.csv) or Excel (.xlsx) file.")
    except UnicodeDecodeError as err:
        raise UploadError("The CSV file is not UTF-8. Save it as 'CSV UTF-8' and try again.") \
            from err
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    if df.empty:
        raise UploadError("The file has no rows of data.")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- matching


def _normal(name: str) -> str:
    return re.sub(r"[^a-z0-9°%]+", " ", name.lower()).strip()


def _looks_like_dates(values: pd.Series) -> bool:
    sample = values.dropna().head(200)
    if sample.empty or pd.to_numeric(sample, errors="coerce").notna().mean() > 0.5:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return parsed.notna().mean() >= 0.9


def suggest_mapping(df: pd.DataFrame) -> dict[str, tuple[str | None, float]]:
    """Guess the standard name of every column, with a confidence from 0 to 1.

    1.0 = our template's name, 0.8 = a name we recognise, 0.6 = guessed from
    the values (dates). Each standard name is given to at most one column.
    """
    guesses: dict[str, tuple[str | None, float]] = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in TEMPLATE:
            guesses[col] = (TEMPLATE[key], 1.0)
            continue
        text = _normal(col)
        found = next((std for std in PRIORITY
                      if any(re.search(p, text) for p in KEYWORDS[std])), None)
        if found:
            guesses[col] = (found, 0.8)
        elif _looks_like_dates(df[col]):
            guesses[col] = ("ts", 0.6)
        else:
            guesses[col] = (None, 0.0)

    best: dict[str, str] = {}  # standard -> column with the highest confidence
    for col, (std, conf) in guesses.items():
        if std and (std not in best or conf > guesses[best[std]][1]):
            best[std] = col
    return {col: (std, conf) if std and best[std] == col else (None, 0.0)
            for col, (std, conf) in guesses.items()}


def guess_units(df: pd.DataFrame, mapping: dict) -> dict[str, str]:
    """Guess each mapped column's unit from its name and values.

    Power: "kW", "W" or "kWh" (energy per interval). Temperature: "C" or "F".
    Humidity: "pct" (0-100) or "fraction" (0-1).
    """
    units = {}
    for col, std in _plain(mapping).items():
        if not std or std == "ts":
            continue
        text = _normal(col)
        values = pd.to_numeric(df[col], errors="coerce")
        if std in POWER:
            if re.search(r"\bkwh\b", text):
                units[std] = "kWh"
            elif re.search(r"\b(w|watts?)\b", text):
                units[std] = "W"
            else:
                units[std] = "kW"
        elif std == "temp_c":
            named_f = re.search(r"(°f|\bdeg ?f\b|\bf\b|fahrenheit)", text)
            units[std] = "F" if named_f or values.max() > 60 else "C"
        elif std == "humidity":
            units[std] = "fraction" if values.max() <= 1.0 else "pct"
    return units


# ---------------------------------------------------------------- converting


def _plain(mapping: dict) -> dict[str, str | None]:
    """Accept {column: name} or {column: (name, confidence)}."""
    return {col: (v[0] if isinstance(v, tuple) else v) for col, v in mapping.items()}


def _parse_times(values: pd.Series, dayfirst: bool | None) -> pd.Series:
    text = values.astype("string").str.strip()
    # Year first (2024-01-31 ...) is never ambiguous.
    if text.dropna().str.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}").all():
        return pd.to_datetime(text, errors="coerce", format="mixed")
    if dayfirst is not None:
        return pd.to_datetime(text, errors="coerce", dayfirst=dayfirst, format="mixed")
    month_first = pd.to_datetime(text, errors="coerce", dayfirst=False, format="mixed")
    day_first = pd.to_datetime(text, errors="coerce", dayfirst=True, format="mixed")
    if month_first.notna().sum() > day_first.notna().sum():
        return month_first
    if day_first.notna().sum() > month_first.notna().sum():
        return day_first
    if not month_first.equals(day_first):
        raise UploadError("The dates are ambiguous (for example 03/04 could be 3 April or "
                          "4 March). Choose day-first or month-first.")
    return month_first


def _parse_numbers(values: pd.Series, col: str) -> tuple[pd.Series, int]:
    text = values.astype("string").str.strip().replace("", pd.NA)
    numbers = pd.to_numeric(text, errors="coerce")
    bad = text.notna() & numbers.isna()
    filled = int(text.notna().sum())
    # A few stray values (up to 1 %) are treated as faulty readings; more is a format problem.
    if filled and bad.sum() / filled > 0.01:
        raise UploadError(f"Column '{col}' has text where numbers are expected "
                          f"(for example '{text[bad].iloc[0]}'). Use plain numbers like "
                          "1053.7, with no commas or units.")
    return numbers.astype(float), int(bad.sum())


def _interval_hours(ts: pd.Series) -> float:
    step = ts.sort_values().diff().dropna()
    step = step[step > pd.Timedelta(0)]
    return step.median().total_seconds() / 3600 if len(step) else 1.0


def apply_mapping(df: pd.DataFrame, mapping: dict, options: dict | None = None
                  ) -> tuple[pd.DataFrame, dict]:
    """Rename, convert units, clean and resample to one row per hour.

    ``options``: ``units`` ({standard: unit}, default from ``guess_units``)
    and ``dayfirst`` (True / False / None = work it out).
    Returns the standard hourly table and a report of what was done.
    """
    options = options or {}
    names = {col: std for col, std in _plain(mapping).items() if std}
    if len(set(names.values())) < len(names):
        raise UploadError("Two columns are matched to the same name. Each name can be used once.")
    chosen = set(names.values())
    if "ts" not in chosen:
        raise UploadError("No date-and-time column was chosen.")
    if "it_kw" not in chosen:
        raise UploadError("No IT power column was chosen. IT power is required.")
    if "total_kw" not in chosen and not chosen & set(PARTS):
        raise UploadError("Total facility power is required, or its parts "
                          "(cooling, pumps, fans, lights, other) so we can add them up.")

    units = {**guess_units(df, mapping), **options.get("units", {})}
    raw = df[list(names)].rename(columns=names)
    report = {"rows_read": len(raw), "faulty_readings": 0}

    ts = _parse_times(raw["ts"], options.get("dayfirst"))
    report["rows_bad_time"] = int(ts.isna().sum())
    table = pd.DataFrame({"ts": ts})
    for std in chosen - {"ts"}:
        values, bad = _parse_numbers(raw[std], std)
        report["faulty_readings"] += bad
        table[std] = values
    table = table.dropna(subset=["ts"])
    if table.empty:
        raise UploadError("None of the dates could be read. Write them as YYYY-MM-DD HH:MM.")
    duplicated = table["ts"].duplicated(keep="first")
    report["duplicates_removed"] = int(duplicated.sum())
    table = table[~duplicated].sort_values("ts").reset_index(drop=True)

    interval = _interval_hours(table["ts"])
    if interval > 1:
        raise UploadError("Readings must be hourly or more often (your file has one every "
                          f"{interval:g} hours).")
    report["interval_minutes"] = round(interval * 60)

    for std in chosen & set(POWER):
        unit = units.get(std, "kW")
        if unit == "W":
            table[std] = table[std] / 1000
        elif unit == "kWh":
            table[std] = table[std] / interval
    if units.get("temp_c") == "F":
        table["temp_c"] = (table["temp_c"] - 32) * 5 / 9
    if units.get("humidity") == "fraction":
        table["humidity"] = table["humidity"] * 100

    parts = [p for p in PARTS if p in table]
    if "total_kw" not in table:
        table["total_kw"] = table["it_kw"] + table[parts].sum(axis=1, min_count=len(parts))

    report["faulty_readings"] += _remove_faulty(table)
    hourly = table.set_index("ts").resample("h").mean()
    mech = [m for m in MECHANICAL if m in hourly]
    if mech:
        hourly["mechanical_kw"] = hourly[mech].sum(axis=1, min_count=len(mech))
    hourly = hourly.reset_index()[[c for c in OUTPUT_ORDER if c in hourly.reset_index()]]

    complete = hourly[["it_kw", "total_kw"]].notna().all(axis=1)
    report.update({
        "hours": len(hourly),
        "missing_hours": int((~complete).sum()),
        "start": hourly["ts"].min(),
        "end": hourly["ts"].max(),
        "columns": [c for c in hourly.columns if c != "ts"],
    })
    return hourly, report


def _remove_faulty(table: pd.DataFrame) -> int:
    """Blank out impossible readings in place and return how many were removed."""
    removed = 0

    def blank(mask: pd.Series, cols) -> None:
        nonlocal removed
        cols = [c for c in cols if c in table]
        removed += int((mask & table[cols].notna().any(axis=1)).sum())
        table.loc[mask, cols] = np.nan

    power = [c for c in POWER if c in table]
    for col in power:
        blank(table[col] < 0, [col])
    blank((table["it_kw"] <= 0) | (table["total_kw"] <= 0), ["it_kw", "total_kw"])
    pue = table["total_kw"] / table["it_kw"]
    blank((pue < PUE_RANGE[0]) | (pue > PUE_RANGE[1]), ["it_kw", "total_kw"])
    if "temp_c" in table:
        blank((table["temp_c"] < -60) | (table["temp_c"] > 60), ["temp_c"])
    if "humidity" in table:
        blank((table["humidity"] < 0) | (table["humidity"] > 100), ["humidity"])
    return removed


# ---------------------------------------------------------------- checks


def check_length(df: pd.DataFrame) -> dict:
    """How much time the data covers, and whether that is enough.

    < 1 month "blocked", 1-6 months "limited", 6-12 months "good", 12+ "best".
    """
    ts = df["ts"].dropna()
    days = ((ts.max() - ts.min()) + pd.Timedelta(hours=1)) / pd.Timedelta(days=1) if len(ts) else 0
    for minimum, level, message in LEVELS:
        if days >= minimum:
            return {"days": round(days, 1), "months": round(days / 30.44),
                    "level": level, "message": message}
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- examples


def template_csv() -> bytes:
    """Our empty template: the column names and two example rows."""
    return (Path(__file__).resolve().parent.parent / "data" / "template"
            / "coolcast_template.csv").read_bytes()


def example_csv(months: int = 6) -> bytes:
    """An example file in the template format, from the development data."""
    df = load_demo_data()
    df = df[df["ts"] < df["ts"].min() + pd.DateOffset(months=months)]
    out = pd.DataFrame({
        "timestamp": df["ts"].dt.strftime("%Y-%m-%d %H:%M"),
        "it_kw": df["it_kw"].round(1),
        "total_kw": df["total_kw"].round(1),
        "cooling_kw": df["cooling_kw"].round(2),
        "pump_kw": df["pump_kw"].round(2),
        "hvac_kw": df["hvac_kw"].round(2),
        "plug_kw": df["plug_kw"].round(2),
        "temp_c": df["temp_c"].round(1),
        "humidity_pct": df["humidity"].round(1),
    })
    return out.to_csv(index=False).encode("utf-8")
