"""Everything that depends on where the data centre is.

From the user's country and city (question 1, required) we get the currency,
the grid CO2 factor, the carbon price (where one is known), the city's
coordinates and its past hourly weather. Only the city's name and coordinates
leave the app, never the user's data.

Sources:
- countries, currencies: config/countries.csv (ISO 3166 / ISO 4217)
- grid CO2: Ember yearly electricity data; India: CEA CO2 Baseline Database v22
- coordinates: Open-Meteo geocoding API
- past weather: Open-Meteo historical weather API (ERA5 reanalysis)
"""

import csv
import json
import math
import time
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

COUNTRIES_PATH = Path(__file__).resolve().parent.parent / "config" / "countries.csv"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT_S = 30
ATTEMPTS = 3
FREE_COOLING_LIMIT_C = 12.8  # wet-bulb below 12.8 °C (55 °F), ENERGY STAR / US DOE guideline
HOURS_PER_YEAR = 8760
ALIASES = {"usa": "US", "u.s.": "US", "america": "US", "uk": "GB", "britain": "GB",
           "great britain": "GB", "england": "GB", "uae": "AE", "south korea": "KR",
           "korea": "KR", "russia": "RU", "czech republic": "CZ", "holland": "NL"}


class LocationError(ValueError):
    """A problem finding the user's location or its data, with a message they can act on."""


# ---------------------------------------------------------------- countries


@lru_cache(maxsize=1)
def load_countries() -> dict[str, dict]:
    """Every country keyed by ISO alpha-2 code, from config/countries.csv."""
    with open(COUNTRIES_PATH, encoding="utf-8") as f:
        return {row["iso2"]: row for row in csv.DictReader(f)}


def country_names() -> list[str]:
    """Country names for the Questions screen's dropdown, in alphabetical order."""
    return sorted(row["country"] for row in load_countries().values())


def find_country(name: str) -> dict:
    """Look a country up by name, ISO code (IN, IND) or a common alias (USA, UK)."""
    countries = load_countries()
    key = name.strip().lower()
    code = ALIASES.get(key, key.upper())
    if code in countries:
        return countries[code]
    for row in countries.values():
        if key in (row["country"].lower(), row["iso3"].lower()):
            return row
    raise LocationError(f"We could not find the country '{name}'. Please choose it from the list.")


def _number(text: str) -> float | None:
    return float(text) if text not in ("", None) else None


# ---------------------------------------------------------------- network


def _get_json(url: str, params: dict) -> dict:
    """GET a JSON API. Kept in one place so tests can replace it."""
    full = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(full, headers={"User-Agent": "CoolCast"})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                return json.load(response)
        except OSError as err:
            if attempt == ATTEMPTS:
                raise LocationError("The location and weather service could not be reached. "
                                    "Please try again in a moment.") from err
            time.sleep(attempt)


# ---------------------------------------------------------------- location


def get_location(country: str, city: str) -> dict:
    """Coordinates of the city, plus the country's currency, grid CO2 and carbon price.

    Returns ``lat, lon, city, country, iso2, timezone, currency, emission_factor``
    (kg CO2/kWh, None if unknown), ``ef_year``, ``ef_source``, ``carbon_price``
    (per tonne CO2, None if not known), ``carbon_price_currency``,
    ``carbon_price_source``, ``price_hint`` (None if not known) and ``price_hint_source``.
    """
    row = find_country(country)
    if not city or not city.strip():
        raise LocationError("Please enter the city where your data centre is.")
    found = _get_json(GEOCODE_URL, {"name": city.strip(), "count": 1, "language": "en",
                                    "format": "json", "countryCode": row["iso2"]})
    results = found.get("results") or []
    if not results:
        raise LocationError(f"We could not find '{city}' in {row['country']}. "
                            "Check the spelling, or try the nearest larger city.")
    place = results[0]
    return {
        "lat": float(place["latitude"]),
        "lon": float(place["longitude"]),
        "city": place.get("name", city),
        "country": row["country"],
        "iso2": row["iso2"],
        "timezone": place.get("timezone"),
        "currency": row["currency"],
        "emission_factor": _number(row["emission_factor"]),
        "ef_year": row["ef_year"] or None,
        "ef_source": row["ef_source"] or None,
        "carbon_price": _number(row["carbon_price"]),
        "carbon_price_currency": row["carbon_price_currency"] or None,
        "carbon_price_source": row["carbon_price_source"] or None,
        "price_hint": _number(row["price_hint"]),
        "price_hint_source": row["price_hint_source"] or None,
    }


# ---------------------------------------------------------------- weather


@lru_cache(maxsize=32)
def _weather_cached(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    data = _get_json(WEATHER_URL, {
        "latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
        "hourly": "temperature_2m,relative_humidity_2m", "timezone": "auto",
    })
    hourly = data.get("hourly") or {}
    if not hourly.get("time"):
        raise LocationError("No past weather was found for this place and period.")
    return pd.DataFrame({
        "ts": pd.to_datetime(hourly["time"]),
        "temp_c": pd.to_numeric(pd.Series(hourly["temperature_2m"]), errors="coerce"),
        "humidity": pd.to_numeric(pd.Series(hourly["relative_humidity_2m"]), errors="coerce"),
    })


def fetch_weather(lat: float, lon: float, start, end) -> pd.DataFrame:
    """Past hourly outdoor temperature (°C) and humidity (%) in the site's local time.

    Results are cached, so the same request is not sent twice in a session.
    """
    start = pd.Timestamp(start).strftime("%Y-%m-%d")
    end = pd.Timestamp(end).strftime("%Y-%m-%d")
    return _weather_cached(round(lat, 2), round(lon, 2), start, end).copy()


def merge_weather(df: pd.DataFrame, weather: pd.DataFrame | None) -> tuple[pd.DataFrame, str]:
    """Add outdoor weather to the standard table.

    Uses the file's own ``temp_c`` / ``humidity`` when at least half the hours
    have them; otherwise the fetched weather. Returns the table and where the
    weather came from: "file", "open-meteo" or "none".
    """
    own = [c for c in ("temp_c", "humidity") if c in df and df[c].notna().mean() >= 0.5]
    if own == ["temp_c", "humidity"]:
        return df, "file"
    if weather is None or weather.empty:
        return df, "file" if own else "none"
    out = df.drop(columns=[c for c in ("temp_c", "humidity") if c not in own], errors="ignore")
    fill = weather.set_index("ts")[[c for c in ("temp_c", "humidity") if c not in own]]
    out = out.merge(fill, left_on="ts", right_index=True, how="left")
    return out, "open-meteo"


# ---------------------------------------------------------------- free cooling


def wet_bulb_c(temp_c, rh_pct):
    """Wet-bulb temperature (°C) from air temperature and relative humidity.

    Stull (2011), J. Appl. Meteor. Climatol. 50, 2267-2269; valid for
    RH 5-99 % and -20 to 50 °C, accuracy about ±1 °C.
    """
    t = np.asarray(temp_c, dtype=float)
    rh = np.asarray(rh_pct, dtype=float)
    tw = (t * np.arctan(0.151977 * np.sqrt(rh + 8.313659)) + np.arctan(t + rh)
          - np.arctan(rh - 1.676331) + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh)
          - 4.686035)
    return float(tw) if tw.ndim == 0 else tw


def free_cooling_hours(weather: pd.DataFrame, limit_c: float = FREE_COOLING_LIMIT_C) -> float:
    """Hours per year cool enough for free cooling (wet-bulb below ``limit_c``).

    Counted over the hours that have weather, then scaled to a full year, so a
    6-month file is not reported as half the hours. None if there is no weather.
    """
    valid = weather[["temp_c", "humidity"]].dropna()
    if valid.empty:
        return None
    cool = wet_bulb_c(valid["temp_c"], valid["humidity"]) < limit_c
    share = float(np.mean(cool))
    return share * HOURS_PER_YEAR if not math.isnan(share) else None
