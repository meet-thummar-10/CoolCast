import os

import pandas as pd

from src.clean import OUTPUT_COLUMNS
from src.data import load_demo_data


def test_columns_and_types():
    df = load_demo_data()
    assert list(df.columns) == OUTPUT_COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(df["ts"])
    for col in OUTPUT_COLUMNS[1:]:
        assert pd.api.types.is_float_dtype(df[col]), col


def test_one_full_year_of_hours():
    df = load_demo_data()
    assert len(df) == 8760
    assert df["ts"].is_monotonic_increasing
    assert not df["ts"].duplicated().any()
    assert (df["ts"].diff().dropna() == pd.Timedelta(hours=1)).all()


def test_mostly_complete_and_consistent():
    df = load_demo_data()
    assert df["total_kw"].notna().mean() > 0.9
    parts = df[["it_kw", "cooling_kw", "pump_kw", "hvac_kw", "plug_kw"]].sum(axis=1)
    ok = df["total_kw"].notna()
    assert (parts[ok] - df.loc[ok, "total_kw"]).abs().max() < 0.01


def test_works_from_any_directory(tmp_path):
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        assert len(load_demo_data()) == 8760
    finally:
        os.chdir(cwd)
