import numpy as np
import pandas as pd
import pytest

from src.clean import (
    OUTPUT_COLUMNS,
    add_totals,
    build_hourly_table,
    clean_power,
    clean_weather,
    f_to_c,
    to_hourly,
)

START = "2020-01-01 00:00"


def raw_power(minutes=120, **overrides):
    """Raw power file in NLR format: one reading per minute."""
    df = pd.DataFrame({
        "ts": pd.date_range(START, periods=minutes, freq="min"),
        "it_power_kw": 1000.0,
        "cooling_kw": 10.0,
        "pump_kw": 12.0,
        "hvac_kw": 8.0,
        "plug_and_light_kw": 3.0,
        "pue": 1.033,
    })
    for col, values in overrides.items():
        df[col] = values
    return df


def raw_weather(minutes=120, temp_f=50.0, humidity=40.0):
    return pd.DataFrame({
        "ts": pd.date_range(START, periods=minutes, freq="min"),
        "outdoor_air_temp": temp_f,
        "outdoor_air_humidity": humidity,
    })


def test_f_to_c():
    assert f_to_c(32) == 0
    assert f_to_c(212) == 100


def test_negative_power_reading_is_removed():
    cooling = np.full(120, 10.0)
    cooling[5] = -3.0
    out = clean_power(raw_power(cooling_kw=cooling))
    assert len(out) == 119
    assert (out["cooling_kw"] >= 0).all()


def test_spike_above_cap_is_removed():
    hvac = np.full(120, 8.0)
    hvac[0] = 5000.0
    assert len(clean_power(raw_power(hvac_kw=hvac))) == 119


def test_minute_with_impossible_pue_is_removed():
    it = np.full(120, 1000.0)
    it[0] = 1.0  # total would be 34 kW on 1 kW of IT -> PUE 34
    assert len(clean_power(raw_power(it_power_kw=it))) == 119


def test_rows_before_breakdown_start_are_removed():
    df = raw_power()
    df.loc[0, "ts"] = pd.Timestamp("2015-12-01")
    assert len(clean_power(df)) == 119


def test_weather_placeholder_and_bad_values():
    df = raw_weather(minutes=3)
    df.loc[0, "ts"] = pd.Timestamp("1970-01-01")
    df.loc[1, "outdoor_air_temp"] = -39.4
    df.loc[2, "outdoor_air_humidity"] = 0.0
    out = clean_weather(df)
    assert len(out) == 2  # 1970 row dropped
    assert out["temp_c"].isna().sum() == 1
    assert out["humidity"].isna().sum() == 1


def test_hour_with_too_few_readings_is_missing():
    df = pd.DataFrame({
        "ts": pd.date_range(START, periods=90, freq="min"),  # 60 + 30 minutes
        "x": 1.0,
    })
    hourly = to_hourly(df, ["x"], min_readings=45)
    assert hourly["x"].iloc[0] == 1.0
    assert np.isnan(hourly["x"].iloc[1])


def test_totals():
    df = pd.DataFrame({"it_kw": [100.0], "cooling_kw": [1.0], "pump_kw": [2.0],
                       "hvac_kw": [3.0], "plug_kw": [4.0]})
    out = add_totals(df)
    assert out["total_kw"].iloc[0] == 110.0
    assert out["mechanical_kw"].iloc[0] == 6.0


def test_build_hourly_table(tmp_path):
    power_path = tmp_path / "power.parquet"
    weather_path = tmp_path / "weather.parquet"
    raw_power(minutes=180).to_parquet(power_path)
    weather = raw_weather(minutes=180, temp_f=50.0)
    weather = weather[weather["ts"] >= pd.Timestamp(START) + pd.Timedelta(hours=1)]
    weather.to_parquet(weather_path)

    table = build_hourly_table(power_path, weather_path)

    assert list(table.columns) == OUTPUT_COLUMNS
    assert len(table) == 3
    assert table["total_kw"].tolist() == pytest.approx([1033.0] * 3)
    assert table["mechanical_kw"].tolist() == pytest.approx([30.0] * 3)
    assert np.isnan(table["temp_c"].iloc[0])  # no weather in the first hour
    assert table["temp_c"].iloc[1] == pytest.approx(10.0)
