import math

import pytest

from app.formatting import (
    MISSING,
    fmt_co2,
    fmt_energy,
    fmt_money,
    fmt_pct,
    fmt_range,
    round_sig,
)


@pytest.mark.parametrize("kwh, text", [
    (950, "950 kWh"),
    (43_800, "43.8 MWh"),
    (2_500_000, "2.5 GWh"),
    (1_234.5, "1.23 MWh"),
    (0.25, "250 Wh"),
    (-43_000, "-43 MWh"),
])
def test_fmt_energy(kwh, text):
    assert fmt_energy(kwh) == text


@pytest.mark.parametrize("amount, currency, text", [
    (344_000, "INR", "₹3.44 lakh"),
    (25_000_000, "INR", "₹2.5 crore"),
    (950, "INR", "₹950"),
    (12_345, "INR", "₹12,345"),
    (-344_000, "INR", "-₹3.44 lakh"),
    (12_500, "USD", "$12,500"),
    (3_400_000, "EUR", "€3.4 million"),
    (1_200_000_000, "GBP", "£1.2 billion"),
    (999_999, "USD", "$999,999"),
])
def test_fmt_money(amount, currency, text):
    assert fmt_money(amount, currency) == text


def test_unknown_currency_raises():
    with pytest.raises(ValueError, match="XYZ"):
        fmt_money(10, "XYZ")


def test_fmt_pct_and_co2():
    assert fmt_pct(0.125) == "12.5%"
    assert fmt_pct(0.1) == "10%"
    assert fmt_co2(30_100) == "30.1 t CO2"
    assert fmt_co2(315) == "315 kg CO2"


def test_round_sig():
    assert round_sig(55_140) == 55_000
    assert round_sig(110_280) == 110_000
    assert round_sig(0.0347) == 0.035


@pytest.mark.parametrize("low, high, fmt, args, text", [
    (55_000, 110_000, fmt_energy, (), "55 – 110 MWh"),
    (55_140, 110_280, fmt_energy, (), "55 – 110 MWh"),
    (110_000, 55_000, fmt_energy, (), "55 – 110 MWh"),
    (0, 106_000, fmt_energy, (), "0 – 110 MWh"),
    (441_000, 882_000, fmt_money, ("INR",), "₹4.4 – 8.8 lakh"),
    (0, 850_000, fmt_money, ("INR",), "₹0 – 8.5 lakh"),
    (950, 1_200, fmt_energy, (), "950 kWh – 1.2 MWh"),
    (176_000, 176_400, fmt_energy, (), "180 MWh"),
    (37_000, 74_000, fmt_co2, (), "37 – 74 t CO2"),
])
def test_fmt_range(low, high, fmt, args, text):
    assert fmt_range(low, high, fmt, *args) == text


@pytest.mark.parametrize("fn", [fmt_energy, fmt_co2, fmt_pct, lambda x: fmt_money(x, "USD")])
def test_missing_values(fn):
    assert fn(None) == MISSING
    assert fn(math.nan) == MISSING
    assert fmt_range(None, 5, fmt_energy) == MISSING
