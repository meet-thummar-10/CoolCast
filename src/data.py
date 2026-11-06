"""Load CoolCast data."""

from pathlib import Path

import pandas as pd

from src.clean import OUTPUT_COLUMNS

DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo" / "demo_hourly.csv"


def load_demo_data() -> pd.DataFrame:
    """Return the demo year (2023) of the clean hourly table.

    One row per hour with the standard columns from docs/contracts.md.
    Hours without enough valid readings have missing values.
    """
    df = pd.read_csv(DEMO_PATH, parse_dates=["ts"])
    return df[OUTPUT_COLUMNS].sort_values("ts").reset_index(drop=True)
