# Interface contract (DRAFT)

Backend writes these functions in `src/`. Frontend calls them from `app/`.
Frontend builds against stub versions that return fake data until the
real ones are merged. Update this file whenever a signature changes.

## Raw to standard column mapping (DRAFT, from the real files)

| Standard name | Raw column | Raw unit | Standard unit | Notes |
|---|---|---|---|---|
| ts | ts | not stated | not applicable | Present in both raw files (`datetime64[us]`). Time zone not stated. |
| it_kw | it_power_kw | kilowatts | kW | Captures power used by IT equipment on the data center floor. |
| cooling_kw | cooling_kw | kilowatts | kW | Captures power used by fans and pipe trace heaters associated with outdoor cooling equipment, plus dedicated tower filter pump power; the 2.67 kW tower filter pump value is attributed (fixed), not metered. |
| pump_kw | pump_kw | kilowatts | kW | Captures power from pumps moving water in the energy recovery water loop (README text: 'Energy Recover Water') and Tower Water loops and fan wall boost pumps; excludes dedicated tower filter pump power (the 2.67 kW tower filter pump value is attributed (fixed), not metered). |
| hvac_kw | hvac_kw | kilowatts | kW | Captures fan walls, fan coils that support the data center electrical rooms, and the make-up air unit. |
| plug_kw | plug_and_light_kw | kilowatts | kW | Captures power associated with the data center and dedicated mechanical room, and the crank-case heater for the emergency standby generator. |
| total_kw | none | not stated | kW | does not exist in raw data; computed as it_power_kw + cooling_kw + hvac_kw + plug_and_light_kw + pump_kw, the five components NLR lists for PUE; checked against the dataset's pue column (median absolute difference 0.00018). |
| mechanical_kw | none | not stated | kW | derived, cooling_kw + pump_kw + hvac_kw, our definition of cooling-system power. |
| temp_c | outdoor_air_temp | Degrees Fahrenheit | degrees C | Listed as `outside_air_temp` in README. In Degrees Fahrenheit (range: -39.400002 to 104.227997 °F); must be converted to Celsius via `(temp_f - 32) * 5/9`. |
| humidity | outdoor_air_humidity | Relative humidity percent | percent | Listed as `outside_air_humidity` in README. Relative humidity percentage (values range from 0.0 to 100.0%). |

Both raw files are timezone-naive and the zone is not stated. We assume they share one clock and use timestamps as given.

## Function signatures

| Function | Inputs | Returns |
|---|---|---|
| `load_demo_data()` | none | DataFrame: `ts, it_kw, cooling_kw, pump_kw, hvac_kw, plug_kw, total_kw, mechanical_kw, temp_c, humidity` |
| `quality_report(df)` | DataFrame | dict: `completeness, missing_hours, longest_gap_h, grade` |
| `compute_kpis(df, tariff, emission_factor)` | DataFrame, number, number | dict: `pue, it_kwh, total_kwh, cooling_share, cost, co2_kg, cue` (ratios are None when there is no IT energy) |
| `pue_by_load(df)` | DataFrame | DataFrame: `load_bin, it_kw_mid, pue, hours` (10 equal-width IT-load bins, empty bins left out) |
| `train_models(df, target="total_kw")` | DataFrame, column name | dict: `models` (name → fitted model), `metrics` DataFrame (`model, mae, rmse, r2`, best first), `predictions` DataFrame (`ts, actual`, one column per model), `best` (model name) |
| `flag_anomalies(df, predictions)` | DataFrame, array | DataFrame: `start, end, hours, excess_kwh` |
| `net_energy(it_kw, pue, reduction, ai_kwh, tariff, ef)` | numbers | dict: `saved_kwh, cost, co2_kg, new_pue, net_kwh` (to be replaced by a range-based savings calculator, see the issues) |

## Planned for the new design (names are fixed in each issue)
- Upload: read a CSV or Excel file, match its columns to the standard names, check data length (< 1 month blocked, 1-6 months warning, 6+ good).
- Location: country and city to coordinates, currency, grid CO2 factor and carbon price; past weather for those coordinates.
- Recommendations: the "How to reduce your cost" steps with ranges (see `docs/assumptions.md`).
- Benchmark: the user's PUE against published global figures.
- Export: PDF report and Excel workbook.

Rules: energy kWh = power kW x interval hours. Annual PUE is a ratio of
sums, never an average of hourly ratios.
