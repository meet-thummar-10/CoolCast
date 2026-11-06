import numpy as np
import pandas as pd
import pytest

from src.clean import COMPONENTS
from src.data import load_demo_data
from src.quality import grade_for, quality_report


def hourly(n=100):
    df = pd.DataFrame({"ts": pd.date_range("2023-01-01", periods=n, freq="h")})
    for col in COMPONENTS:
        df[col] = 10.0
    return df


def test_complete_data():
    assert quality_report(hourly()) == {
        "completeness": 1.0, "missing_hours": 0, "longest_gap_h": 0, "grade": "A",
    }


def test_ten_missing_hours():
    df = hourly()
    df.loc[10:19, "cooling_kw"] = np.nan
    report = quality_report(df)
    assert report["completeness"] == pytest.approx(0.9)
    assert report["missing_hours"] == 10
    assert report["longest_gap_h"] == 10
    assert report["grade"] == "B"


def test_rows_absent_from_table_count_as_missing():
    df = hourly().drop(index=range(40, 45))
    report = quality_report(df)
    assert report["missing_hours"] == 5
    assert report["longest_gap_h"] == 5


def test_longest_gap_picks_the_longest_run():
    df = hourly()
    df.loc[[5, 6], "it_kw"] = np.nan
    df.loc[50:53, "it_kw"] = np.nan
    assert quality_report(df)["longest_gap_h"] == 4


@pytest.mark.parametrize("value, grade", [(1.0, "A"), (0.98, "A"), (0.97, "B"), (0.9, "B"),
                                          (0.89, "C"), (0.75, "C"), (0.74, "D"), (0.0, "D")])
def test_grade_boundaries(value, grade):
    assert grade_for(value) == grade


def test_empty_table():
    assert quality_report(hourly(0))["grade"] == "D"


def test_demo_data():
    report = quality_report(load_demo_data())
    assert report["grade"] == "B"
    assert 0.9 < report["completeness"] < 0.98
