# Interface contract

Backend writes these functions in `src/`. Frontend calls them from `app/`.
Update this file whenever a signature changes.

## Development data: raw to standard column mapping

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
| `compute_kpis(df, tariff, emission_factor)` | DataFrame, number, number | dict: `pue, it_kwh, total_kwh, cooling_share, cost, co2_kg, cue` (ratios are None when there is no IT energy; `cooling_share` is None without cooling columns). Needs only `ts, it_kw, total_kw` |
| `pue_by_load(df)` | DataFrame | DataFrame: `load_bin, it_kw_mid, pue, hours` (10 equal-width IT-load bins, empty bins left out) |
| `train_models(df, target="total_kw")` | DataFrame, column name | dict: `models` (name → fitted model), `metrics` DataFrame (`model, mae, rmse, r2`, best first), `predictions` DataFrame (`ts, actual`, one column per model), `best` (model name) |
| `flag_anomalies(df, predictions, tariff, threshold_kw=None, target="total_kw")` | DataFrame, forecast (time-indexed Series or one value per row), price per kWh | DataFrame: `start, end, hours, excess_kwh, excess_cost`, largest first. Default threshold: 3 × standard deviation of the residuals |
| `best_predictions(result)` | result of `train_models` | Series: the best model's forecast, indexed by time |
| `savings_range(it_kwh, pue, cut_low, cut_high, it_off_low, it_off_high, tariff, ef, one_off_cost=0)` | numbers (cuts in %, 0-100) | dict of `(low, high)` pairs: `kwh, money, co2_kg, new_pue` (best, worst), `payback_years` (shortest, longest or None) or None; and `verdict` (`likely`, `uncertain`, `none`) |

## Uploaded files (`src/upload.py`)

Standard hourly table: `ts`, `it_kw`, `total_kw` always; `cooling_kw`, `pump_kw`,
`hvac_kw`, `plug_kw`, `other_kw`, `mechanical_kw`, `temp_c`, `humidity` only when
the file has them. Missing readings are empty (NaN), never 0.

| Function | Inputs | Returns |
|---|---|---|
| `read_file(file, name=None)` | path or file-like (.csv UTF-8 or .xlsx, up to 200 MB) | DataFrame of text cells |
| `suggest_mapping(df)` | raw DataFrame | dict: column → (standard name or None, confidence 0-1) |
| `guess_units(df, mapping)` | raw DataFrame, mapping | dict: standard name → unit (`kW`/`W`/`kWh`, `C`/`F`, `pct`/`fraction`) |
| `apply_mapping(df, mapping, options=None)` | raw DataFrame, mapping, `{units, dayfirst}` | (standard hourly table, report: `rows_read, rows_bad_time, duplicates_removed, faulty_readings, interval_minutes, hours, missing_hours, start, end, columns`) |
| `check_length(df)` | standard table | dict: `days, months, level` (`blocked` < 1 month, `limited` 1-6, `good` 6-12, `best` 12+), `message` |
| `template_csv()`, `example_csv(months=6)` | none | CSV bytes for the Upload screen's download buttons |

Problems with a user's file raise `UploadError` (a `ValueError`) with a message the user can act on.

## Location (`src/location.py`)

Only the city's name and coordinates leave the app, never the user's data.

| Function | Inputs | Returns |
|---|---|---|
| `country_names()` | none | list of country names for the dropdown (from `config/countries.csv`) |
| `find_country(name)` | name, ISO code or alias (USA, UK) | row: `country, iso2, iso3, currency, emission_factor, ef_year, ef_source, ...` |
| `get_location(country, city)` | names | dict: `lat, lon, city, country, iso2, timezone, currency, emission_factor, ef_year, ef_source, carbon_price, carbon_price_currency, carbon_price_source, price_hint, price_hint_source` (unknown values are None) |
| `fetch_weather(lat, lon, start, end)` | coordinates, dates | DataFrame: `ts, temp_c, humidity` (hourly, local time; cached) |
| `merge_weather(df, weather)` | standard table, weather or None | (table, source: `file`, `open-meteo` or `none`) |
| `wet_bulb_c(temp_c, rh_pct)` | numbers or arrays | wet-bulb temperature in °C (Stull 2011) |
| `free_cooling_hours(weather, limit_c=12.8)` | DataFrame with `temp_c, humidity` | hours per year below the limit, or None |

Problems raise `LocationError` (a `ValueError`) with a message the user can act on.

## Recommendations (`src/recommend.py`)

| Function | Inputs | Returns |
|---|---|---|
| `OPTIONS` | constant | answer codes for questions 3-10: `site_type, cooling_system, free_cooling, vfd, ups_mode, unused_servers, can_change` |
| `recommend(df, kpis, answers, location=None)` | standard table, `compute_kpis` result, answers, `{emission_factor, free_cooling_hours}` | dict: `steps` (list), `skipped` (list of `{id, reason}`), `period_hours`. Each step: `id, title, effort (free / small / large), confidence, found, todo, low_kwh, high_kwh, low_money, high_money, low_co2_kg, high_co2_kg, per, calc, warning, sources, label`. Free cooling has no range (None). No total is ever returned |
| `overhead_split(df)` | standard table | dict: `always_on, follows_servers, follows_weather` (fractions; weather is None without temperature), `r2, hours`; None with fewer than 48 usable hours |

Answers (`st.session_state["answers"]`): `country, city, price, currency, site_type,
cooling_system, free_cooling, supply_temp_c, vfd, ups_mode, unused_servers, can_change`.
"I don't know" is stored as None.

## Benchmark (`src/benchmark.py`)

| Function | Inputs | Returns |
|---|---|---|
| `load_benchmarks()` | none | dict from `config/benchmarks.toml`: key → `name, pue, year, source, link` |
| `monthly_pue(df)` | standard table | Series: PUE per month (months with at least a week of data) |
| `benchmark_pue(df, tariff)` | standard table, price per kWh | dict: `pue, month_min, month_max, references` (DataFrame: `name, source, year, link, pue, overhead_per_100, overhead_for_you_kwh`), `avoided_kwh, avoided_money` (vs the global average), `low_pue_warning` (PUE below 1.1) |

## Export (`src/export.py`)

| Function | Inputs | Returns |
|---|---|---|
| `collect_results(df, answers, location=None, file_name=None)` | standard table, answers, location | the `results` dict (below) |
| `build_excel(results)` | results | .xlsx bytes: sheets Summary, Monthly, Anomalies, Steps to reduce cost, Forecast, Your answers and settings, Data quality; each with a `label` column |
| `build_pdf(results)` | results | PDF bytes: key numbers, steps with ranges, benchmark, anomalies, forecast accuracy, answers, data quality, method |
| `monthly_table(df, tariff)` | standard table, price per kWh | DataFrame: `month, it_kwh, total_kwh, pue, cost` |

## The app (`app/`)

Stages (`st.session_state["stage"]`): `landing` → `upload` → `questions` → `analysing`
→ `analysis`. There is no sidebar before `analysis`.

| Function | Inputs | Returns |
|---|---|---|
| `app.state.go_to(stage)`, `exit_analysis()` | stage name | move to a stage; delete the user's data and return to the landing page |
| `app.pipeline.run_analysis(data, answers, upload_report=None, file_name=None, report=...)` | clean table, answers, upload report, progress callback `(step, status, detail)` | the `results` dict plus `weather_source` and `table` (the table with weather added) |
| `app.page_utils.page_start(title, lead)` | text | the current results, or a "no analysis yet" message and stop |
| `app.page_utils.current_results()` | none | results with money and CO2 recalculated for the sidebar's price and CO2 factor |
| `app.page_utils.settings()` | none | `(tariff, emission_factor, currency)` |
| `app.formatting.fmt_energy`, `fmt_co2`, `fmt_pct`, `fmt_money(amount, currency)`, `fmt_range(low, high, fmt, ...)` | numbers | display text; ranges are rounded to 2 significant figures |
| `app.components.kpi_card(label, value, tag)`, `status_box(kind, text)`, `line_chart`, `bar_chart`, `scatter`, `heatmap`, `empty_state`, `error_state` | see the file | UI pieces; `tag` is measured / modelled / assumed / estimate, `kind` is good / check / problem |

Session keys: `stage, data` (clean hourly table), `file_name, upload_report, data_level,
answers, results, tariff, emission_factor` (the last two are the sidebar inputs).

`results` keys: `file_name, period, currency, tariff, kpis, quality, monthly, anomalies,
steps, forecast, forecast_target, benchmark, overhead, answers, location, weather_source`.

Rules: energy kWh = power kW x interval hours. Annual PUE is a ratio of
sums, never an average of hourly ratios.
