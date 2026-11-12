"""How to reduce your cost: steps that fit the user's site, each with a careful range.

Rules (docs/assumptions.md):
- every range comes from a published source and is applied only to the part
  of the energy it affects
- ranges are estimates, the low end can be 0, and they are never added together
- savings are for the period covered by the user's data (not stretched to a
  year, which would mislead for short or seasonal files)
- a step is skipped, with a reason, when the user's answers or data rule it out
"""

import numpy as np
import pandas as pd

from src.metrics import complete_rows, interval_hours

# Answer codes stored by the Questions screen. "I don't know" is stored as None.
OPTIONS = {
    "site_type": {
        "enterprise": "Our own company's (enterprise)",
        "colocation": "Colocation (we host others' servers)",
        "edge": "Small or edge site",
        "cloud": "Cloud / hyperscale",
        "hpc": "Research / HPC",
    },
    "cooling_system": {
        "air_chillers": "Air-cooled chillers",
        "water_chillers": "Water-cooled chillers with cooling towers",
        "crac_dx": "Room air-conditioning units (CRAC / DX)",
        "evaporative": "Evaporative or adiabatic cooling",
        "liquid": "Liquid cooling",
        "other": "Other",
    },
    "free_cooling": {"air": "Yes, with outside air", "water": "Yes, with cool water (water-side)",
                     "no": "No"},
    "vfd": {"all": "Yes, all of them", "some": "Some of them", "none": "None"},
    "ups_mode": {"double_conversion": "Normal (double-conversion)",
                 "eco": "Eco / efficiency mode already", "mix": "A mix"},
    "unused_servers": {"regularly": "Yes, regularly", "sometimes": "Sometimes", "never": "Never"},
    "can_change": {"free": "Free setting changes only", "small": "Small investments too",
                   "large": "Larger projects too"},
}

MAX_SUPPLY_C = 27.0          # top of the ASHRAE recommended range
MIN_SUPPLY_C = 18.0          # bottom of the ASHRAE recommended range
SETPOINT_PER_C = (0.02, 0.04)
VFD_RANGE = (0.0, 0.27)
UPS_RANGE = {"double_conversion": (0.0, 0.02), "mix": (0.0, 0.01)}
LIGHTING_RANGE = (0.10, 0.25)
FREE_COOLING_SUITABLE_H = 3000
BASE_TEMP_C = 10.0           # cooling degrees are counted above this outdoor temperature

SOURCES = {
    "setpoint": "Cell Reports Physical Science (2-6 % of cooling energy per °C; the cautious "
                "2-4 % is used); ASHRAE recommended range 18-27 °C via LBNL; ENERGY STAR",
    "vfd": "Affinity law: 10 % slower ≈ 27 % less energy (ASHE); US DOE on variable-speed drives",
    "servers": "Uptime Institute (15-30 % of equipment idle without regular checks); "
               "Koomey / Anthesis study of comatose servers",
    "ups": "ENERGY STAR (eco mode can cut data-centre energy costs by up to 2 %); "
           "US DOE FEMP best-practices guide",
    "lighting": "LBNL (occupancy sensors saved 20-26 % of lighting energy in measured offices)",
    "free_cooling": "ENERGY STAR / US DOE (water-side economisers suit climates with ≥ 3,000 "
                    "hours a year below 12.8 °C wet-bulb; DOE study: 2.3-year payback)",
}


# ---------------------------------------------------------------- overhead split


def overhead_split(df: pd.DataFrame, base_c: float = BASE_TEMP_C) -> dict | None:
    """Split overhead power into always on / follows the servers / follows the weather.

    Fits overhead (total − IT, kW) = a + b × IT + c × max(temperature − base_c, 0)
    by least squares, then reports each term's share of the fitted overhead
    energy. Without temperature, only the first two terms are fitted.

    Returns ``always_on, follows_servers, follows_weather`` (fractions, or None
    for weather when there is no temperature), ``r2`` and ``hours``; None if
    there are fewer than 48 usable hours.
    """
    rows = complete_rows(df)
    has_weather = "temp_c" in rows and rows["temp_c"].notna().mean() >= 0.5
    if has_weather:
        rows = rows.dropna(subset=["temp_c"])
    if len(rows) < 48:
        return None
    overhead = (rows["total_kw"] - rows["it_kw"]).to_numpy()
    columns = [np.ones(len(rows)), rows["it_kw"].to_numpy()]
    if has_weather:
        columns.append((rows["temp_c"] - base_c).clip(lower=0).to_numpy())
    x = np.column_stack(columns)
    coef, *_ = np.linalg.lstsq(x, overhead, rcond=None)
    fitted = x @ coef
    ss_tot = ((overhead - overhead.mean()) ** 2).sum()
    r2 = float(1 - ((overhead - fitted) ** 2).sum() / ss_tot) if ss_tot else 0.0

    # Energy in each part; a negative part (a fit artefact) counts as 0.
    parts = np.clip(coef * x.sum(axis=0), 0, None)
    shares = parts / parts.sum() if parts.sum() else parts
    return {
        "always_on": float(shares[0]),
        "follows_servers": float(shares[1]),
        "follows_weather": float(shares[2]) if has_weather else None,
        "r2": r2,
        "hours": int(len(rows)),
    }


# ---------------------------------------------------------------- steps


def _energy(rows: pd.DataFrame, cols: list[str], hours: float) -> float | None:
    """Energy (kWh) of the given columns over the complete rows; None if any column is absent."""
    if not all(c in rows and rows[c].notna().any() for c in cols):
        return None
    return float(rows[cols].sum(axis=1, min_count=len(cols)).sum() * hours)


def _step(sid, title, effort, confidence, found, todo, low_kwh, high_kwh, calc, warning,
          tariff, ef, per=None):
    has_range = low_kwh is not None
    return {
        "id": sid, "title": title, "effort": effort, "confidence": confidence,
        "found": found, "todo": todo,
        "low_kwh": low_kwh, "high_kwh": high_kwh,
        "low_money": low_kwh * tariff if has_range else None,
        "high_money": high_kwh * tariff if has_range else None,
        "low_co2_kg": low_kwh * ef if has_range and ef is not None else None,
        "high_co2_kg": high_kwh * ef if has_range and ef is not None else None,
        "per": per, "calc": calc, "warning": warning, "sources": SOURCES[sid],
        "label": "estimate",
    }


def recommend(df: pd.DataFrame, kpis: dict, answers: dict, location: dict | None = None
              ) -> dict:
    """The cost-reduction steps that apply to this site.

    ``answers`` uses the codes in ``OPTIONS`` (None = "I don't know") plus
    ``price`` (per kWh, from the bill) and ``supply_temp_c``. ``location`` may
    give ``emission_factor`` and ``free_cooling_hours``.

    Returns ``{"steps": [...], "skipped": [{"id", "reason"}], "period_hours"}``.
    Each step has ``id, title, effort ("free" | "small" | "large"), confidence,
    found, todo, low_kwh, high_kwh, low_money, high_money, low_co2_kg,
    high_co2_kg, per, calc, warning, sources, label``. Ranges are never added up.
    """
    location = location or {}
    tariff = float(answers.get("price") or 0)
    ef = location.get("emission_factor", answers.get("emission_factor"))
    rows = complete_rows(df)
    hours = interval_hours(df)
    steps, skipped = [], []

    def skip(sid, reason):
        skipped.append({"id": sid, "reason": reason})

    # 1. Raise the cooling setpoint (free).
    cooling = _energy(rows, ["mechanical_kw"], hours)
    supply = answers.get("supply_temp_c")
    if cooling is None:
        skip("setpoint", "Your file has no cooling columns, so the cooling energy is unknown.")
    elif supply is not None and float(supply) >= MAX_SUPPLY_C:
        skip("setpoint", "You already supply 27 °C or more, the top of the recommended range.")
    else:
        assumed = supply is None
        headroom = 1.0 if assumed else MAX_SUPPLY_C - max(float(supply), MIN_SUPPLY_C)
        start = ("an unknown temperature (we assume 1 °C of room)" if assumed
                 else f"{float(supply):g} °C")
        steps.append(_step(
            "setpoint", "Raise the cooling temperature setpoint, gradually", "free", "medium",
            f"You supply {start} to the servers. The recommended range goes up to 27 °C, so "
            f"there is up to {headroom:g} °C of room. Your cooling system used "
            f"{cooling / 1000:,.0f} MWh in this period.",
            "Raise the supply temperature in steps of about 1 °C, checking server inlet "
            "temperatures and hot spots after each step. Stop at 27 °C.",
            cooling * SETPOINT_PER_C[0] * headroom, cooling * SETPOINT_PER_C[1] * headroom,
            f"2-4 % of cooling-system energy per °C × {headroom:g} °C",
            "Going above 27 °C can increase total energy because server fans speed up. "
            "Raising temperature is safer with hot/cold aisle containment.", tariff, ef))

    # 2. Variable-speed pumps and fans (small investment).
    pumps_fans = _energy(rows, ["pump_kw", "hvac_kw"], hours)
    if answers.get("vfd") == "all":
        skip("vfd", "All your pumps and fans already have variable-speed drives.")
    elif pumps_fans is None:
        skip("vfd", "Your file has no pump and fan columns.")
    else:
        steps.append(_step(
            "vfd", "Let pumps and fans slow down when full speed is not needed", "small",
            "low to medium",
            f"Pumps and fans used {pumps_fans / 1000:,.0f} MWh in this period. "
            + ("Some of them have variable-speed drives." if answers.get("vfd") == "some"
               else "Not all of them may have variable-speed drives."),
            "Fit variable-speed drives where missing and let pumps and fans follow the actual "
            "cooling demand instead of running at full speed.",
            pumps_fans * VFD_RANGE[0], pumps_fans * VFD_RANGE[1],
            "Up to 27 % of pump and fan energy (running 10 % slower); 0 % if already optimised",
            "This is a theoretical maximum from the affinity law; real systems save less because "
            "of friction and pressure limits. Get an engineer's assessment.", tariff, ef))

    # 3. Switch off unused servers (free).
    if answers.get("site_type") == "colocation":
        skip("servers", "As a colocation provider you cannot switch off customers' servers.")
    elif answers.get("unused_servers") == "regularly":
        skip("servers", "You already find and remove unused servers regularly.")
    else:
        per_pct = kpis["it_kwh"] * 0.01 * kpis["pue"]
        steps.append(_step(
            "servers", "Find and switch off unused servers", "free", "high (for the formula)",
            "Studies estimate 15-30 % of equipment can sit idle in sites without regular checks.",
            "Run an audit: list servers with no useful work for several months, confirm with "
            "their owners, then switch them off or remove them.",
            per_pct, per_pct,
            f"Each 1 % of IT power switched off × your IT energy × your PUE {kpis['pue']:.3f} "
            "(removing IT also removes its cooling). We do not guess how many are idle.",
            "Only remove servers after their owners confirm they are unused.", tariff, ef,
            per="1 % of IT power switched off"))

    # 4. UPS efficiency mode (free).
    ups = answers.get("ups_mode")
    if ups == "eco":
        skip("ups", "Your UPS units already run in an efficiency mode.")
    else:
        lo, hi = UPS_RANGE.get(ups or "double_conversion")
        total = kpis["total_kwh"]
        steps.append(_step(
            "ups", "Review your UPS efficiency mode with your supplier", "free", "low",
            {"mix": "Some of your UPS units run in normal (double-conversion) mode.",
             None: "We do not know how your UPS units run."}.get(
                ups, "Your UPS units run in normal (double-conversion) mode."),
            "Ask your UPS supplier whether an efficiency mode is safe for your loads and power "
            "quality, and test it on one unit first.",
            total * lo, total * hi, f"Up to {hi:.0%} of total facility energy",
            "Efficiency modes reduce power protection. Never switch without your supplier's "
            "advice.", tariff, ef))

    # 5. Lighting sensors (small investment).
    lights = _energy(rows, ["plug_kw"], hours)
    if lights is None:
        skip("lighting", "Your file has no lighting column.")
    else:
        steps.append(_step(
            "lighting", "Put data-hall lights on sensors or timers", "small", "medium",
            f"Your file includes lights and plugs: {lights / 1000:,.1f} MWh in this period.",
            "Fit occupancy sensors or timers so lights are on only when people are inside.",
            lights * LIGHTING_RANGE[0], lights * LIGHTING_RANGE[1],
            "10-25 % of lights-and-plugs energy (an upper estimate, because it includes plugs)",
            "A small saving: worth doing, but lower priority than the steps above.", tariff, ef))

    # 6. Free cooling (larger project): feasibility only, no range.
    free_h = location.get("free_cooling_hours")
    if answers.get("free_cooling") in ("air", "water"):
        skip("free_cooling", "You already use free cooling.")
    elif free_h is None:
        skip("free_cooling", "No weather was available for your location.")
    else:
        suitable = free_h >= FREE_COOLING_SUITABLE_H
        steps.append(_step(
            "free_cooling", "Use outside air or cool water to cool for free", "large",
            "medium (for feasibility)",
            f"Your city's past weather had {free_h:,.0f} hours a year cool enough "
            "(wet-bulb below 12.8 °C).",
            "Ask a cooling engineer for a free-cooling (economiser) feasibility study."
            if suitable else
            "Your climate has fewer than 3,000 suitable hours a year, so free cooling is "
            "unlikely to pay back; discuss only as part of a larger redesign.",
            None, None,
            f"{'Suitable' if suitable else 'Not very suitable'} climate: {free_h:,.0f} hours a "
            "year (guideline: 3,000 or more). No saving range: it depends too much on the "
            "building.",
            "Adding free cooling to an existing site is a major project; savings and payback "
            "need a site-specific study.", tariff, ef))

    return {"steps": steps, "skipped": skipped, "period_hours": float(len(rows) * hours)}
