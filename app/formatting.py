"""Format numbers for display: energy, money in any currency, percent, CO2 and ranges.

Every function returns "–" for missing values (None or NaN).
"""

import math
import re

MISSING = "–"

# ISO code -> symbol. INR uses lakh and crore; every other currency uses
# thousands, "million" and "billion".
CURRENCIES = {
    "INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "SGD": "S$", "AUD": "A$",
    "CAD": "C$", "NZD": "NZ$", "HKD": "HK$", "JPY": "¥", "CNY": "CN¥", "KRW": "₩",
    "CHF": "CHF ", "SEK": "SEK ", "NOK": "NOK ", "DKK": "DKK ", "PLN": "zł ",
    "AED": "AED ", "SAR": "SAR ", "QAR": "QAR ", "ZAR": "R ", "BRL": "R$",
    "MXN": "MX$", "IDR": "Rp ", "MYR": "RM ", "THB": "฿", "PHP": "₱", "VND": "₫",
    "TRY": "₺", "ILS": "₪", "NGN": "₦", "KES": "KSh ", "EGP": "E£", "PKR": "Rs ",
    "BDT": "৳", "LKR": "Rs ", "TWD": "NT$", "CLP": "CLP$", "COP": "COL$",
}


def _is_missing(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _trim(text: str) -> str:
    return text.rstrip("0").rstrip(".") if "." in text else text


def _sig(x: float, digits: int = 3) -> str:
    """Round to ``digits`` significant figures and drop trailing zeros."""
    if x == 0:
        return "0"
    decimals = max(digits - 1 - math.floor(math.log10(abs(x))), 0)
    return _trim(f"{x:,.{decimals}f}")


def round_sig(x: float, digits: int = 2) -> float:
    """Round a number to ``digits`` significant figures (55_140 -> 55_000)."""
    if x == 0 or _is_missing(x):
        return x
    return round(x, digits - 1 - math.floor(math.log10(abs(x))))


def _scaled(value: float, units: list[tuple[float, str]]) -> str:
    """Pick the largest unit the value reaches; units are (size, name), smallest first."""
    size, name = units[0]
    for unit_size, unit_name in units:
        if abs(value) >= unit_size:
            size, name = unit_size, unit_name
    return f"{_sig(value / size)} {name}"


def fmt_energy(kwh) -> str:
    """Energy in kWh -> "950 kWh", "43.8 MWh", "2.5 GWh" (below 1 kWh: Wh)."""
    if _is_missing(kwh):
        return MISSING
    return _scaled(kwh, [(0.001, "Wh"), (1, "kWh"), (1e3, "MWh"), (1e6, "GWh")])


def fmt_co2(kg) -> str:
    """CO2 in kg -> "315 kg CO2", "30.1 t CO2" (below 1 kg: grams)."""
    if _is_missing(kg):
        return MISSING
    return _scaled(kg, [(0.001, "g CO2"), (1, "kg CO2"), (1e3, "t CO2")])


def fmt_pct(fraction, decimals: int = 1) -> str:
    """Fraction -> percent: 0.125 -> "12.5%", 0.1 -> "10%"."""
    if _is_missing(fraction):
        return MISSING
    return f"{_trim(f'{fraction * 100:.{decimals}f}')}%"


def fmt_money(amount, currency: str) -> str:
    """Money in the user's currency (ISO code).

    INR: "₹950", "₹12,345", "₹3.44 lakh", "₹2.5 crore".
    Others: "$12,500", "€3.4 million", "£1.2 billion".
    A valid ISO code without a known symbol is written in front: "UGX 12,500".
    """
    if currency not in CURRENCIES and not re.fullmatch(r"[A-Z]{3}", currency or ""):
        raise ValueError(f"Unknown currency code {currency!r}")
    if _is_missing(amount):
        return MISSING
    symbol = CURRENCIES.get(currency, f"{currency} ")
    sign = "-" if amount < 0 else ""
    value = abs(amount)
    if currency == "INR":
        steps = [(1e7, " crore"), (1e5, " lakh")]
    else:
        steps = [(1e9, " billion"), (1e6, " million")]
    for size, word in steps:
        if value >= size:
            return f"{sign}{symbol}{_trim(f'{value / size:,.2f}')}{word}"
    return f"{sign}{symbol}{value:,.0f}"


_PARTS = re.compile(r"^(-?\D*?)(\d[\d,]*(?:\.\d+)?)(.*)$")


def fmt_range(low, high, fmt, *args, **kwargs) -> str:
    """A range rounded to 2 significant figures, sharing the symbol and unit.

    ``fmt_range(55_000, 110_000, fmt_energy)`` -> "55 – 110 MWh";
    ``fmt_range(0, 850_000, fmt_money, "INR")`` -> "₹0 – 8.5 lakh".
    Returns a single value if both ends round to the same number.
    """
    if _is_missing(low) or _is_missing(high):
        return MISSING
    low, high = sorted((round_sig(low), round_sig(high)))
    hi_text = fmt(high, *args, **kwargs)
    if low == high:
        return hi_text
    lo_text = fmt(low, *args, **kwargs)
    lo, hi = _PARTS.match(lo_text), _PARTS.match(hi_text)
    if lo and hi:
        if low == 0:
            return f"{hi.group(1)}0 – {hi.group(2)}{hi.group(3)}"
        if lo.group(1) == hi.group(1) and lo.group(3) == hi.group(3):
            return f"{hi.group(1)}{lo.group(2)} – {hi.group(2)}{hi.group(3)}"
    return f"{lo_text} – {hi_text}"
