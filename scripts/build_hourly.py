"""Build data/processed/hourly.parquet from the raw NLR files and print a summary."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.clean import build_hourly_table  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "hourly.parquet"
POWER = RAW / "esif.influx.buildingData.PUE.combined.parquet"
WEATHER = RAW / "esif.influx.buildingData.outside.combined.parquet"
NLR_ANNUAL_PUE = 1.036


def main() -> None:
    for path in (POWER, WEATHER):
        if not path.exists():
            raise SystemExit(f"Missing {path}. See docs/data.md for the download links.")

    table = build_hourly_table(POWER, WEATHER)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(OUT, index=False)

    complete = table.dropna(subset=["total_kw"])
    print(f"Saved {OUT.relative_to(ROOT)}: {len(table)} hours "
          f"({table.ts.min()} to {table.ts.max()})")
    print(f"Hours with power data:   {len(complete)} ({len(complete) / len(table):.1%})")
    print(f"Hours with weather data: {table.temp_c.notna().sum()} "
          f"({table.temp_c.notna().mean():.1%})")

    print("\nAnnual PUE (ratio of sums):")
    yearly = complete.groupby(complete.ts.dt.year)[["total_kw", "it_kw"]].sum()
    for year, row in yearly.iterrows():
        print(f"  {year}: {row.total_kw / row.it_kw:.4f}")
    overall = complete.total_kw.sum() / complete.it_kw.sum()
    print(f"  All years: {overall:.4f}  (NLR published annualised PUE: {NLR_ANNUAL_PUE})")


if __name__ == "__main__":
    main()
