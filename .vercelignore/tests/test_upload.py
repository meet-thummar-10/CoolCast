import io

import numpy as np
import pandas as pd
import pytest

from src.upload import (
    UploadError,
    apply_mapping,
    check_length,
    example_csv,
    guess_units,
    read_file,
    suggest_mapping,
    template_csv,
)


def raw(rows, **cols):
    """A raw upload: every cell as text, like read_file returns."""
    return pd.DataFrame({k: [None if v is None else str(v) for v in vals]
                         for k, vals in cols.items()})


def hours(n, start="2024-01-01", freq="h", fmt="%Y-%m-%d %H:%M"):
    return list(pd.date_range(start, periods=n, freq=freq).strftime(fmt))


# ------------------------------------------------------------ reading


def test_read_csv_and_excel(tmp_path):
    df = pd.DataFrame({"timestamp": hours(3), "it_kw": [1, 2, 3], "total_kw": [2, 3, 4]})
    csv, xlsx = tmp_path / "a.csv", tmp_path / "a.xlsx"
    df.to_csv(csv, index=False)
    df.to_excel(xlsx, index=False)
    for path in (csv, xlsx):
        out = read_file(path)
        assert list(out.columns) == ["timestamp", "it_kw", "total_kw"]
        assert out["it_kw"].tolist() == ["1", "2", "3"]


def test_read_file_like_object_and_wrong_type():
    buf = io.BytesIO(b"timestamp,it_kw\n2024-01-01 00:00,5\n")
    buf.name = "upload.csv"
    assert len(read_file(buf)) == 1
    bad = io.BytesIO(b"x")
    bad.name = "data.json"
    with pytest.raises(UploadError, match="CSV"):
        read_file(bad)


# ------------------------------------------------------------ matching


def test_template_names_match_exactly():
    df = raw(1, timestamp=["2024-01-01 00:00"], it_kw=[1], total_kw=[2], humidity_pct=[50])
    m = suggest_mapping(df)
    assert m["timestamp"] == ("ts", 1.0)
    assert m["humidity_pct"] == ("humidity", 1.0)


def test_other_names_are_recognised():
    df = raw(1, **{"Date/Time": ["01/02/2024 00:00"], "IT Load (W)": [2_000_000],
                   "Facility Total kW": [2500], "Chiller kW": [100], "CHW Pump": [20],
                   "CRAH fans": [30], "Lights": [5], "OAT (°F)": [75], "RH": [0.5],
                   "Notes": ["ok"]})
    m = {col: std for col, (std, _) in suggest_mapping(df).items()}
    assert m == {"Date/Time": "ts", "IT Load (W)": "it_kw", "Facility Total kW": "total_kw",
                 "Chiller kW": "cooling_kw", "CHW Pump": "pump_kw", "CRAH fans": "hvac_kw",
                 "Lights": "plug_kw", "OAT (°F)": "temp_c", "RH": "humidity", "Notes": None}
    units = guess_units(df, m)
    assert units["it_kw"] == "W" and units["temp_c"] == "F" and units["humidity"] == "fraction"


def test_date_column_found_from_values():
    df = raw(3, reading_at=hours(3), a=[1, 2, 3])
    assert suggest_mapping(df)["reading_at"] == ("ts", 0.6)


def test_each_name_used_once():
    df = raw(1, **{"Total kW": [1], "Total power": [1]})
    names = [std for std, _ in suggest_mapping(df).values()]
    assert names.count("total_kw") == 1


# ------------------------------------------------------------ converting

MAP = {"timestamp": "ts", "it_kw": "it_kw", "total_kw": "total_kw"}


def test_watts_become_kilowatts():
    df = raw(2, timestamp=hours(2), it=[2_000_000, 2_000_000], total=[2_500_000, 2_500_000])
    out, _ = apply_mapping(df, {"timestamp": "ts", "it": "it_kw", "total": "total_kw"},
                           {"units": {"it_kw": "W", "total_kw": "W"}})
    assert out["it_kw"].tolist() == [2000, 2000]


def test_kwh_per_15_minutes_become_hourly_kw():
    df = raw(8, timestamp=hours(8, freq="15min"), it_kw=[25] * 8, total_kw=[30] * 8)
    out, report = apply_mapping(df, MAP, {"units": {"it_kw": "kWh", "total_kw": "kWh"}})
    assert report["interval_minutes"] == 15
    assert len(out) == 2
    assert out["it_kw"].tolist() == [100, 100]
    assert out["total_kw"].tolist() == [120, 120]


def test_fahrenheit_and_fraction_humidity():
    df = raw(2, timestamp=hours(2), it_kw=[10, 10], total_kw=[12, 12], t=[75, 32], h=[0.5, 0.25])
    out, _ = apply_mapping(df, {**MAP, "t": "temp_c", "h": "humidity"},
                           {"units": {"temp_c": "F", "humidity": "fraction"}})
    assert out["temp_c"].round(1).tolist() == [23.9, 0.0]
    assert out["humidity"].tolist() == [50, 25]


def test_total_is_added_up_from_the_parts():
    df = raw(2, timestamp=hours(2), it_kw=[100, 100], cooling_kw=[10, 10], pump_kw=[5, 5],
             plug_kw=[1, None])
    mapping = {c: c if c != "timestamp" else "ts" for c in df.columns}
    out, _ = apply_mapping(df, mapping)
    assert out["total_kw"].iloc[0] == 116
    assert np.isnan(out["total_kw"].iloc[1])  # a missing part is not treated as 0
    assert out["mechanical_kw"].iloc[0] == 15


def test_repeated_timestamps_are_removed_and_counted():
    ts = hours(3)
    df = raw(4, timestamp=[ts[0], ts[1], ts[1], ts[2]], it_kw=[1, 2, 9, 3], total_kw=[2, 3, 9, 4])
    out, report = apply_mapping(df, MAP)
    assert report["duplicates_removed"] == 1
    assert out["it_kw"].tolist() == [1, 2, 3]


def test_gaps_stay_empty_and_faulty_readings_are_removed():
    df = raw(4, timestamp=[*hours(2), *hours(2, start="2024-01-01 04:00")],
             it_kw=[100, -5, 100, 100], total_kw=[120, 120, 50, 120])
    out, report = apply_mapping(df, MAP)
    assert len(out) == 6  # 00:00 to 05:00, hours 02:00 and 03:00 are gaps
    assert out["it_kw"].isna().sum() == 4  # 2 gaps, 1 negative, 1 with total below IT
    assert report["faulty_readings"] == 2
    assert report["missing_hours"] == 4


def test_ambiguous_dates_need_a_choice():
    df = raw(2, timestamp=["03/04/2024 00:00", "03/04/2024 01:00"], it_kw=[1, 1], total_kw=[2, 2])
    with pytest.raises(UploadError, match="day-first"):
        apply_mapping(df, MAP)
    out, _ = apply_mapping(df, MAP, {"dayfirst": True})
    assert out["ts"].iloc[0] == pd.Timestamp("2024-04-03 00:00")


def test_day_first_is_worked_out_when_clear():
    df = raw(2, timestamp=["25/04/2024 00:00", "25/04/2024 01:00"], it_kw=[1, 1], total_kw=[2, 2])
    out, _ = apply_mapping(df, MAP)
    assert out["ts"].iloc[0] == pd.Timestamp("2024-04-25 00:00")


@pytest.mark.parametrize("mapping, message", [
    ({"it_kw": "it_kw", "total_kw": "total_kw"}, "date"),
    ({"timestamp": "ts", "total_kw": "total_kw"}, "IT power"),
    ({"timestamp": "ts", "it_kw": "it_kw"}, "Total facility power"),
    ({"timestamp": "ts", "it_kw": "it_kw", "total_kw": "it_kw"}, "same name"),
])
def test_clear_errors_for_missing_columns(mapping, message):
    df = raw(2, timestamp=hours(2), it_kw=[1, 1], total_kw=[2, 2])
    with pytest.raises(UploadError, match=message):
        apply_mapping(df, mapping)


def test_text_in_number_columns():
    df = raw(3, timestamp=hours(3), it_kw=["1,053.7", "1,054.0", "1,055.1"], total_kw=[2, 2, 2])
    with pytest.raises(UploadError, match="plain numbers"):
        apply_mapping(df, MAP)


def test_readings_less_often_than_hourly_are_refused():
    df = raw(3, timestamp=hours(3, freq="D"), it_kw=[1, 1, 1], total_kw=[2, 2, 2])
    with pytest.raises(UploadError, match="hourly"):
        apply_mapping(df, MAP)


# ------------------------------------------------------------ length


@pytest.mark.parametrize("n_hours, level", [
    (12 * 24, "blocked"),
    (90 * 24, "limited"),
    (200 * 24, "good"),
    (8760, "best"),
])
def test_check_length(n_hours, level):
    df = pd.DataFrame({"ts": pd.date_range("2023-01-01", periods=n_hours, freq="h")})
    assert check_length(df)["level"] == level


# ------------------------------------------------------------ files


def test_template_and_example_files_load_cleanly():
    tpl = read_file(io.BytesIO(template_csv()), name="t.csv")
    assert all(conf == 1.0 for _, conf in suggest_mapping(tpl).values())

    df = read_file(io.BytesIO(example_csv()), name="example.csv")
    out, report = apply_mapping(df, suggest_mapping(df))
    assert report["duplicates_removed"] == 0
    assert check_length(out)["level"] == "good"
    assert {"it_kw", "total_kw", "mechanical_kw", "temp_c", "humidity"} <= set(out.columns)
