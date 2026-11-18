import numpy as np
import pandas as pd
import pytest

from src import location
from src.location import (
    LocationError,
    country_names,
    fetch_weather,
    find_country,
    free_cooling_hours,
    get_location,
    merge_weather,
    wet_bulb_c,
)

REAL_GET_JSON = location._get_json  # saved before the fixture replaces it

PLACES = {
    ("Pune", "IN"): {"name": "Pune", "latitude": 18.52, "longitude": 73.86,
                     "timezone": "Asia/Kolkata"},
    ("Frankfurt", "DE"): {"name": "Frankfurt am Main", "latitude": 50.11, "longitude": 8.68,
                          "timezone": "Europe/Berlin"},
}


def weather_json(hours=48):
    times = pd.date_range("2023-07-01", periods=hours, freq="h").strftime("%Y-%m-%dT%H:%M")
    return {"hourly": {"time": list(times), "temperature_2m": [20.0] * hours,
                       "relative_humidity_2m": [50] * hours}}


@pytest.fixture(autouse=True)
def fake_network(monkeypatch):
    """No real network in tests: answer like the Open-Meteo APIs do."""
    calls = []

    def fake(url, params):
        calls.append((url, params))
        if url == location.GEOCODE_URL:
            place = PLACES.get((params["name"], params["countryCode"]))
            return {"results": [place]} if place else {}
        return weather_json()

    monkeypatch.setattr(location, "_get_json", fake)
    location._weather_cached.cache_clear()
    return calls


def test_india_uses_rupees_and_the_cea_factor():
    loc = get_location("India", "Pune")
    assert loc["currency"] == "INR"
    assert loc["emission_factor"] == 0.675
    assert "CEA" in loc["ef_source"]
    assert (loc["lat"], loc["lon"]) == (18.52, 73.86)


def test_germany_uses_euros_and_ember():
    loc = get_location("Germany", "Frankfurt")
    assert loc["currency"] == "EUR"
    assert 0 < loc["emission_factor"] < 1
    assert "Ember" in loc["ef_source"]


@pytest.mark.parametrize("name, iso2", [
    ("india", "IN"), ("IN", "IN"), ("IND", "IN"), ("USA", "US"), ("United States", "US"),
    ("UK", "GB"), ("United Kingdom", "GB"),
])
def test_find_country_by_name_code_or_alias(name, iso2):
    assert find_country(name)["iso2"] == iso2


def test_every_country_has_a_currency_and_valid_factors():
    rows = location.load_countries().values()
    assert len(rows) > 200
    for row in rows:
        assert len(row["currency"]) == 3, row["country"]
        if row["emission_factor"]:
            assert 0 <= float(row["emission_factor"]) < 1.5, row["country"]
            assert row["ef_source"] and row["ef_year"], row["country"]
    assert "India" in country_names() and country_names() == sorted(country_names())


@pytest.mark.parametrize("country, city, message", [
    ("Atlantis", "Pune", "country"),
    ("India", "Xyzzy", "could not find 'Xyzzy'"),
    ("India", "  ", "enter the city"),
])
def test_clear_errors(country, city, message):
    with pytest.raises(LocationError, match=message):
        get_location(country, city)


def test_service_down_gives_a_clear_error(monkeypatch):
    def down(*args, **kwargs):
        raise OSError("no connection")

    monkeypatch.setattr(location, "ATTEMPTS", 2)
    monkeypatch.setattr(location.time, "sleep", lambda s: None)
    monkeypatch.setattr(location.urllib.request, "urlopen", down)
    with pytest.raises(LocationError, match="could not be reached"):
        REAL_GET_JSON(location.GEOCODE_URL, {"name": "Pune"})


def test_fetch_weather_returns_hourly_rows_and_is_cached(fake_network):
    a = fetch_weather(18.52, 73.86, "2023-07-01", "2023-07-02")
    b = fetch_weather(18.52, 73.86, "2023-07-01", "2023-07-02")
    assert len(a) == 48 and list(a.columns) == ["ts", "temp_c", "humidity"]
    pd.testing.assert_frame_equal(a, b)
    assert sum(url == location.WEATHER_URL for url, _ in fake_network) == 1


def test_wet_bulb_stull():
    assert wet_bulb_c(20, 50) == pytest.approx(13.7, abs=0.3)
    assert wet_bulb_c(35, 20) < 35
    assert np.allclose(wet_bulb_c([20, 20], [50, 50]), [13.7, 13.7], atol=0.3)


def test_free_cooling_hours_scaled_to_a_year():
    weather = pd.DataFrame({"temp_c": [5.0, 5.0, 30.0, 30.0], "humidity": [50.0] * 4})
    assert free_cooling_hours(weather) == pytest.approx(8760 / 2)
    assert free_cooling_hours(weather.assign(temp_c=np.nan)) is None


def test_merge_weather_prefers_the_file():
    ts = pd.date_range("2023-07-01", periods=3, freq="h")
    fetched = pd.DataFrame({"ts": ts, "temp_c": [1.0, 2, 3], "humidity": [10.0, 20, 30]})
    own = pd.DataFrame({"ts": ts, "it_kw": 1.0, "temp_c": [9.0, 9, 9], "humidity": [90.0] * 3})
    out, source = merge_weather(own, fetched)
    assert source == "file" and out["temp_c"].tolist() == [9, 9, 9]

    bare = own[["ts", "it_kw"]]
    out, source = merge_weather(bare, fetched)
    assert source == "open-meteo" and out["temp_c"].tolist() == [1, 2, 3]

    out, source = merge_weather(bare, None)
    assert source == "none" and "temp_c" not in out
