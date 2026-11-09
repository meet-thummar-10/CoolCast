"""Cut one year from data/processed/hourly.parquet into data/demo/demo_hourly.csv.

Run scripts/build_hourly.py first.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "processed" / "hourly.parquet"
OUT = ROOT / "data" / "demo" / "demo_hourly.csv"

# 2023: typical PUE (1.034, close to NLR's 1.036) and 92 % complete, with a
# few real gaps for the quality report to show.
DEMO_YEAR = 2023


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing {SOURCE}. Run: python scripts/build_hourly.py")
    table = pd.read_parquet(SOURCE)
    demo = table[table["ts"].dt.year == DEMO_YEAR]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    demo.to_csv(OUT, index=False, float_format="%.3f", date_format="%Y-%m-%d %H:%M")
    size_kb = OUT.stat().st_size / 1024
    print(f"Saved {OUT.relative_to(ROOT)}: {len(demo)} hours of {DEMO_YEAR}, {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
