# Assumptions

Every value below is an **assumption**, not a measurement. The app labels
any number that depends on them as *assumed* or *modelled*. The values live
in `config/assumptions.toml`; change them there, not in code.

| Name | Default | Unit | Why this value |
|---|---|---|---|
| `tariff` | 8.0 | ₹/kWh | Typical Indian commercial electricity tariff (roughly ₹7-10/kWh). Users can change it in the sidebar. |
| `emission_factor` | 0.675 | kg CO2/kWh | Weighted average grid emission factor from the CEA CO2 Baseline Database for the Indian Power Sector, version 22.0 (FY 2025-26): 0.675 tCO2/MWh. Earlier versions: 0.716 (v19, FY 2022-23), 0.727 (v20, FY 2023-24). Update when CEA publishes a new version. |
| `greenest_tolerance` | 0.05 | fraction of best MAE | A model may be up to 5 % less accurate than the most accurate one if it uses less energy. Used by `pick_greenest()`. |
| `cooling_reduction` | 0.10 | fraction of cooling overhead | Scenario: AI-guided control cuts cooling overhead by 10 %. Used by the savings calculator. |

## Important
- The NLR data comes from a facility in Colorado, USA. The tariff and
  emission factor are Indian values, chosen because the project's results
  are presented for an Indian context. Cost and CO2 figures are therefore
  scenarios, not the facility's real cost or emissions.
- Savings are scenarios. CoolCast does not control any cooling system.
