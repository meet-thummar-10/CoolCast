# Interface contract (DRAFT)

Backend writes these functions in `src/`. Frontend calls them from `app/`.
Frontend builds against stub versions that return fake data until the
real ones are merged. Update this file whenever a signature changes.

**Column names are not confirmed yet. Update after loading the real files.**

| Function | Inputs | Returns |
|---|---|---|
| `load_demo_data()` | none | DataFrame: `ts, it_kw, cooling_kw, pump_kw, other_kw, total_kw, temp_c, humidity` |
| `quality_report(df)` | DataFrame | dict: `completeness, missing_hours, longest_gap_h, grade` |
| `compute_kpis(df, tariff, emission_factor)` | DataFrame, number, number | dict: `pue, it_kwh, total_kwh, cooling_share, cost, co2_kg, cue` |
| `pue_by_load(df)` | DataFrame | DataFrame: `load_bin, pue` |
| `train_models(df)` | DataFrame | dict of fitted models and a metrics DataFrame (`model, mae, rmse, r2`) |
| `benchmark_energy(model, X)` | model, features | dict: `train_wh, infer_wh_per_1k, co2_g` |
| `pick_greenest(metrics_df, tolerance)` | DataFrame, number | model name |
| `flag_anomalies(df, predictions)` | DataFrame, array | DataFrame: `start, end, hours, excess_kwh` |
| `net_energy(it_kw, pue, reduction, ai_kwh, tariff, ef)` | numbers | dict: `saved_kwh, cost, co2_kg, new_pue, net_kwh` |

Rules: energy kWh = power kW x interval hours. Annual PUE is a ratio of
sums, never an average of hourly ratios.
