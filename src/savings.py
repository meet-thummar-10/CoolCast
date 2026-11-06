"""Savings calculator: does AI-guided cooling save more energy than the AI uses?

All results are scenarios (label: modelled). CoolCast does not control any
cooling system.
"""

HOURS_PER_YEAR = 8760


def _check_inputs(it_kw, pue, reduction, ai_kwh, tariff, ef) -> None:
    if pue < 1:
        raise ValueError(f"PUE cannot be below 1 (got {pue})")
    if not 0 <= reduction <= 1:
        raise ValueError(f"reduction must be between 0 and 1 (got {reduction})")
    for name, value in {"it_kw": it_kw, "ai_kwh": ai_kwh, "tariff": tariff, "ef": ef}.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative (got {value})")


def net_energy(it_kw: float, pue: float, reduction: float, ai_kwh: float,
               tariff: float, ef: float) -> dict:
    """Yearly savings if cooling overhead drops by ``reduction``, minus the AI's own energy.

    Args:
        it_kw: average IT load (kW)
        pue: current PUE (at least 1)
        reduction: fraction of the overhead (PUE - 1) removed, 0 to 1
        ai_kwh: energy the AI uses per year (kWh), e.g. training plus predictions
        tariff: electricity price (₹/kWh)
        ef: grid emission factor (kg CO2/kWh)

    Returns ``{saved_kwh, cost, co2_kg, new_pue, net_kwh}`` where ``saved_kwh``
    is the gross saving, ``net_kwh`` is the saving after the AI's energy, and
    ``cost`` and ``co2_kg`` are the money and CO2 saved on ``net_kwh``.
    A negative ``net_kwh`` means the AI uses more energy than it saves.
    """
    _check_inputs(it_kw, pue, reduction, ai_kwh, tariff, ef)
    it_kwh = it_kw * HOURS_PER_YEAR
    overhead_kwh = (pue - 1) * it_kwh
    saved_kwh = overhead_kwh * reduction
    net_kwh = saved_kwh - ai_kwh
    return {
        "saved_kwh": saved_kwh,
        "cost": net_kwh * tariff,
        "co2_kg": net_kwh * ef,
        "new_pue": pue - (pue - 1) * reduction,
        "net_kwh": net_kwh,
    }
