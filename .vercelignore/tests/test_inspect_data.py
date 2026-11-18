import pandas as pd

from scripts.inspect_data import find_timestamp


def test_finds_datetime_column():
    df = pd.DataFrame({"x": [1], "when": pd.to_datetime(["2024-01-01"])})
    assert find_timestamp(df) == "when"


def test_finds_column_by_name():
    df = pd.DataFrame({"value": [1], "ts": ["2024-01-01"]})
    assert find_timestamp(df) == "ts"


def test_returns_none_without_timestamp():
    assert find_timestamp(pd.DataFrame({"a": [1]})) is None
