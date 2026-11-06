"""Print a summary of every Parquet file in data/raw/."""

from pathlib import Path

import pandas as pd

# Resolve from the repo root so the script works from any directory.
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
TS_NAMES = ("ts", "timestamp", "time", "datetime")


def find_timestamp(df: pd.DataFrame):
    """Return the name of the timestamp column, or None."""
    for col in df.columns:
        if str(df[col].dtype).startswith("datetime") or col.lower() in TS_NAMES:
            return col
    return None


def summarise(path: Path) -> None:
    """Print shape, types, missing values, time range and stats of one file."""
    df = pd.read_parquet(path)
    if df.index.name:
        df = df.reset_index()

    print("=" * 70)
    print(f"{path.name}: {df.shape[0]} rows, {df.shape[1]} columns")
    print("\nColumns and types:")
    print(df.dtypes.to_string())
    print("\nMissing values per column:")
    print(df.isna().sum().to_string())
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())

    ts_col = find_timestamp(df)
    if ts_col is None:
        print("\nNo timestamp column found automatically. Check the columns above.")
    else:
        ts = pd.to_datetime(df[ts_col]).sort_values()
        print(f"\nTime range: {ts.min()} to {ts.max()}")
        step = ts.diff().dropna().mode()
        print("Most common step between rows:", step.iloc[0] if len(step) else "n/a")

    print("\nNumeric summary:")
    print(df.describe().T.to_string())


if __name__ == "__main__":
    files = sorted(RAW.glob("*.parquet"))
    if not files:
        raise SystemExit(f"No .parquet files in {RAW}. Download them first.")
    for file in files:
        summarise(file)
