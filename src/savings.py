"""Savings calculator: turn the user's low and high guesses into saving ranges.

Two changes are modelled together:
- a cut in overhead (cooling, pumps, UPS losses...): the part of PUE above 1
- IT power switched off (unused servers), which also removes the overhead it caused

Results are estimates (label: estimate) shown as ranges, never single numbers.
CoolCast does not control any equipment.
"""

LIKELY, UNCERTAIN, NONE = "likely", "uncertain", "none"


def _pct(name: str, value: float) -> float:
    if not 0 <= value <= 100:
        raise ValueError(f"{name} must be a percentage between 0 and 100 (got {value})")
    return value / 100


def _check(it_kwh, pue, tariff, ef, one_off_cost) -> None:
    if pue < 1:
        raise ValueError(f"PUE cannot be below 1 (got {pue})")
    values = {"it_kwh": it_kwh, "tariff": tariff, "ef": ef, "one_off_cost": one_off_cost}
    for name, value in values.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative (got {value})")


def _after(it_kwh: float, pue: float, cut: float, it_off: float) -> float:
    """Total energy after the changes: remaining IT x (1 + remaining overhead share)."""
    return it_kwh * (1 - it_off) * (1 + (pue - 1) * (1 - cut))


def savings_range(it_kwh: float, pue: float, cut_low: float, cut_high: float,
                  it_off_low: float, it_off_high: float, tariff: float, ef: float,
                  one_off_cost: float = 0) -> dict:
    """Yearly saving range from low and high guesses.

    Args:
        it_kwh: IT energy per year (kWh), from the user's data
        pue: current PUE (at least 1), from the user's data
        cut_low, cut_high: cut in overhead, % (0-100), in either order
        it_off_low, it_off_high: IT power switched off, % (0-100), in either order
        tariff: electricity price per kWh in the user's currency
        ef: grid emission factor (kg CO2/kWh)
        one_off_cost: cost of making the changes, same currency (0 = not given)

    Returns a dict where each value is ``(low, high)``:
    ``kwh``, ``money``, ``co2_kg`` (saved per year), ``new_pue`` (best, worst),
    ``payback_years`` (shortest, longest; longest is None when the low saving
    is 0) or None when there is no cost or no saving, and ``verdict``:
    "likely" (even the low end saves), "uncertain" (low end is 0) or "none".
    """
    _check(it_kwh, pue, tariff, ef, one_off_cost)
    cuts = sorted((_pct("cut_low", cut_low), _pct("cut_high", cut_high)))
    offs = sorted((_pct("it_off_low", it_off_low), _pct("it_off_high", it_off_high)))

    today = it_kwh * pue
    low = today - _after(it_kwh, pue, cuts[0], offs[0])
    high = today - _after(it_kwh, pue, cuts[1], offs[1])
    low, high = max(low, 0.0), max(high, 0.0)

    def new_pue(cut: float) -> float:
        # Switching off IT removes its overhead too, so PUE depends only on the cut.
        return 1 + (pue - 1) * (1 - cut)

    money = (low * tariff, high * tariff)
    payback = None
    if one_off_cost > 0 and money[1] > 0:
        payback = (one_off_cost / money[1], one_off_cost / money[0] if money[0] > 0 else None)

    verdict = LIKELY if low > 0 else UNCERTAIN if high > 0 else NONE
    return {
        "kwh": (low, high),
        "money": money,
        "co2_kg": (low * ef, high * ef),
        "new_pue": (new_pue(cuts[1]), new_pue(cuts[0])),
        "payback_years": payback,
        "verdict": verdict,
    }
