"""Clean the raw NLR power and weather files into one hourly table.

The rules here are documented in docs/data.md ("Cleaning rules").
"""

from pathlib import Path

import pandas as pd

# Raw column name -> standard column name (see docs/contracts.md).
POWER_COLUMNS = {
    "it_power_kw": "it_kw",
    "cooling_kw": "cooling_kw",
    "pump_kw": "pump_kw",
    "hvac_kw": "hvac_kw",
    "plug_and_light_kw": "plug_kw",
}
WEATHER_COLUMNS = {"outdoor_air_temp": "temp_f", "outdoor_air_humidity": "humidity"}

COMPONENTS = list(POWER_COLUMNS.values())
MECHANICAL = ["cooling_kw", "pump_kw", "hvac_kw"]
OUTPUT_COLUMNS = ["ts", *COMPONENTS, "total_kw", "mechanical_kw", "temp_c", "humidity"]

# Before this time the power file has no per-component breakdown.
POWER_START = pd.Timestamp("2016-06-12 06:00")

# Upper limits (kW) for one-minute readings. Values above these are spikes
# far beyond normal operation (99.99th percentiles: cooling 62, hvac 216).
POWER_CAPS = {"it_kw": 5000.0, "cooling_kw": 150.0, "pump_kw": 150.0,
              "hvac_kw": 500.0, "plug_kw": 50.0}
PUE_RANGE = (1.0, 3.0)

TEMP_F_RANGE = (-30.0, 115.0)

# An hour is kept only if it has at least this many valid readings.
MIN_POWER_READINGS = 45   # power is logged every minute
MIN_WEATHER_READINGS = 20  # weather is logged every 1 or 2 minutes


def f_to_c(temp_f):
    """Convert degrees Fahrenheit to degrees Celsius."""
    return (temp_f - 32) * 5 / 9


def clean_power(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one-minute power readings with standard names and invalid values removed.

    A minute is kept only if all five components are valid, so totals and
    PUE are always computed from a complete set.
    """
    df = raw.reset_index() if raw.index.name else raw
    df = df[["ts", *POWER_COLUMNS]].rename(columns=POWER_COLUMNS)
    df = df[df["ts"] >= POWER_START].copy()

    for col, cap in POWER_CAPS.items():
        df[col] = df[col].where((df[col] >= 0) & (df[col] <= cap))
    df = df.dropna(subset=COMPONENTS)

    pue = df[COMPONENTS].sum(axis=1) / df["it_kw"]
    df = df[pue.between(*PUE_RANGE)]
    return df.reset_index(drop=True)


def clean_weather(raw: pd.DataFrame) -> pd.DataFrame:
    """Return weather readings in degrees C with invalid values set to missing."""
    df = raw.reset_index() if raw.index.name else raw
    df = df[["ts", *WEATHER_COLUMNS]].rename(columns=WEATHER_COLUMNS)
    df = df[df["ts"] >= POWER_START].copy()  # also drops the 1970 placeholder row

    temp_ok = df["temp_f"].between(*TEMP_F_RANGE)
    df["temp_c"] = f_to_c(df["temp_f"].where(temp_ok))
    # 0 % humidity does not occur outdoors; those readings are sensor dropouts.
    df["humidity"] = df["humidity"].where((df["humidity"] > 0) & (df["humidity"] <= 100))
    return df[["ts", "temp_c", "humidity"]].reset_index(drop=True)


def to_hourly(df: pd.DataFrame, columns: list[str], min_readings: int) -> pd.DataFrame:
    """Average readings into hours labelled by their start time.

    Each column is averaged separately and set to missing for hours with
    fewer than ``min_readings`` valid readings.
    """
    hour = df["ts"].dt.floor("h")
    grouped = df[columns].groupby(hour)
    means = grouped.mean()
    counts = grouped.count()
    hourly = means.where(counts >= min_readings)
    hourly.index.name = "ts"
    return hourly


def add_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Add total facility power and cooling-system (mechanical) power."""
    df = df.copy()
    df["total_kw"] = df[COMPONENTS].sum(axis=1, min_count=len(COMPONENTS))
    df["mechanical_kw"] = df[MECHANICAL].sum(axis=1, min_count=len(MECHANICAL))
    return df


def build_hourly_table(power_path: Path, weather_path: Path) -> pd.DataFrame:
    """Build the clean hourly table from the two raw Parquet files.

    Returns one row per hour from the first to the last hour with power
    data. Hours without enough valid readings are kept with missing values,
    so gaps stay visible to the quality report.
    """
    power = clean_power(pd.read_parquet(power_path))
    weather = clean_weather(pd.read_parquet(weather_path))

    power_h = to_hourly(power, COMPONENTS, MIN_POWER_READINGS)
    # Power columns are only usable together, so drop hours missing any of them.
    power_h = power_h.where(power_h.notna().all(axis=1))
    weather_h = to_hourly(weather, ["temp_c", "humidity"], MIN_WEATHER_READINGS)

    grid = pd.date_range(power_h.index.min(), power_h.index.max(), freq="h", name="ts")
    table = power_h.reindex(grid).join(weather_h, how="left")
    table = add_totals(table).reset_index()
    return table[OUTPUT_COLUMNS]
