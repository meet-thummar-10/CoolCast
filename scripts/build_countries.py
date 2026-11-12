"""Rebuild config/countries.csv from public sources.

Run: python scripts/build_countries.py
Downloads:
- ISO country and currency codes (datasets/country-codes on GitHub)
- Ember yearly electricity data (latest emissions intensity per country)
India uses the official CEA factor instead (CEA CO2 Baseline Database v22).
Carbon price and price-hint columns are kept from the existing file, because
they are filled in by hand from verified sources.
"""

import csv
import io
import urllib.request
from pathlib import Path

CODES_URL = "https://raw.githubusercontent.com/datasets/country-codes/master/data/country-codes.csv"
EMBER_URL = ("https://files.ember-energy.org/public-downloads/generation/outputs/"
             "release_generation_yearly_global.csv")
OUT = Path(__file__).resolve().parent.parent / "config" / "countries.csv"
NAME_FIXES = {"UK": "United Kingdom", "US": "United States"}
OFFICIAL = {  # countries where an official national factor replaces Ember
    "IND": ("0.675", "2025", "CEA CO2 Baseline Database for the Indian Power Sector, "
                             "version 22.0 (FY 2025-26), weighted average"),
}
MANUAL = ["carbon_price", "carbon_price_currency", "carbon_price_source", "price_hint",
          "price_hint_source"]


def download(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=120) as response:
        return list(csv.DictReader(io.TextIOWrapper(response, encoding="utf-8")))


def main() -> None:
    latest: dict[str, tuple[int, float]] = {}
    for row in download(EMBER_URL):
        value = row["Emissions intensity (gCO2e/kWh)"]
        if (row["Area type"] != "Country or economy"
                or row["Electricity source"] != "Total generation" or not value):
            continue
        iso3, year = row["ISO 3 code"], int(row["Year"])
        if iso3 not in latest or year > latest[iso3][0]:
            latest[iso3] = (year, float(value))

    kept = {}
    if OUT.exists():
        with open(OUT, encoding="utf-8") as f:
            kept = {r["iso2"]: r for r in csv.DictReader(f)}

    rows = []
    for c in download(CODES_URL):
        iso2, iso3 = c["ISO3166-1-Alpha-2"], c["ISO3166-1-Alpha-3"]
        currency = (c["ISO4217-currency_alphabetic_code"] or "").split(",")[0].strip()
        name = c["CLDR display name"] or c["UNTERM English Short"] or c["official_name_en"]
        if not (iso2 and currency and name):
            continue
        ef = year = source = ""
        if iso3 in latest:
            year, grams = latest[iso3]
            ef = f"{grams / 1000:.3f}"
            source = ("Ember yearly electricity data, emissions intensity of generation "
                      f"(lifecycle gCO2e/kWh), {year}")
        if iso3 in OFFICIAL:
            ef, year, source = OFFICIAL[iso3]
        row = {"country": NAME_FIXES.get(name, name), "iso2": iso2, "iso3": iso3,
               "currency": currency, "emission_factor": ef, "ef_year": str(year),
               "ef_source": source}
        row.update({k: kept.get(iso2, {}).get(k, "") for k in MANUAL})
        rows.append(row)

    rows.sort(key=lambda r: r["country"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} countries to {OUT}")


if __name__ == "__main__":
    main()
