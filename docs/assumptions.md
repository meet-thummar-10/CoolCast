# Assumptions

Every value below is an **assumption**, not a measurement. The app labels
any number that depends on them as *assumed* or *modelled*. The values live
in `config/assumptions.toml`; change them there, not in code.

| Name | Default | Unit | Why this value |
|---|---|---|---|
| `tariff` | 8.0 | ₹/kWh | Fallback for development and tests only (typical Indian commercial tariff, roughly ₹7-10/kWh). In the app the price comes from the user's own bill (question 2, required); the national average is shown only as a hint. |
| `emission_factor` | 0.675 | kg CO2/kWh | Fallback for development and tests only: CEA CO2 Baseline Database for the Indian Power Sector, version 22.0 (FY 2025-26). In the app the factor comes from the user's location (Ember data or the official national factor). |

## Values that come from the user's location
Country and city (question 1, required) set:
- **Currency** of all money results (with that currency's number format,
  for example lakh/crore for ₹, thousands/millions for $ and €)
- **Past local weather** (Open-Meteo, ERA5) for forecasts and free-cooling hours
- **Grid CO2 factor** (Ember or the official national factor)
- **Carbon price**, where one applies (World Bank Carbon Pricing Dashboard)

## Saving ranges used by "How to reduce your cost"
Each range is applied only to the part of the energy it affects, is
labelled "Estimate", is rounded to 2 significant figures, and is never
added to the others. The low end can be 0.

| Step | Range used | Applied to | Source |
|---|---|---|---|
| Raise cooling setpoint (up to 27 °C) | 2-4 % per °C of headroom | cooling-system energy | Cell Reports Physical Science (2-6 %/°C; cautious half used); ASHRAE 18-27 °C via LBNL; ENERGY STAR |
| Variable-speed pumps and fans | 0-27 % | pump and fan energy | Affinity law, 10 % slower ≈ 27 % less (ASHE); US DOE |
| Switch off unused servers | per 1 % of IT power, × PUE | IT energy | Uptime Institute (15-30 % comatose); Koomey / Anthesis |
| UPS efficiency mode | 0-2 % | total facility energy | ENERGY STAR; US DOE FEMP |
| Lighting sensors | 10-25 % | lights and plugs energy | LBNL (20-26 % measured) |
| Free cooling | feasibility only, no range | hours with wet-bulb below 12.8 °C (≥ 3,000 h/yr suits) | ENERGY STAR / US DOE |

## Important
- The development data comes from a facility in Colorado, USA, and is
  never shown to users. The fallback tariff and emission factor are Indian
  example values, so development figures are scenarios, not that
  facility's real cost or emissions.
- Savings are estimates. CoolCast does not control any equipment.
