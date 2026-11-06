# Data

## Source
NLR HPC Facility Power Usage Effectiveness (PUE) Data
https://data.nlr.gov/submissions/300 (CC BY 4.0)

## Files to download into data/raw/
Save them under these names:

| Dataset page link | Save as |
|---|---|
| ESIF DC Power Metrics Timeseries Data (Parquet) | `esif.influx.buildingData.PUE.combined.parquet` |
| ESIF DC Outside Weather Station Timeseries Data (Parquet) | `esif.influx.buildingData.outside.combined.parquet` |
| README | `README.md` |

Then run `python scripts/inspect_data.py` to print a summary of each file.

## Cleaning rules
`python scripts/build_hourly.py` applies these rules (code: `src/clean.py`) and
writes `data/processed/hourly.parquet`, which is not committed.

| Step | Rule | Effect on the raw data |
|---|---|---|
| Start time | Drop power rows before 2016-06-12 06:00 (no per-component breakdown) and the 1970 weather placeholder row | 136,484 power rows, 1 weather row |
| Negative power | Any component below 0 kW is invalid | cooling 113, pump 475, hvac 428 readings |
| Power spikes | cooling > 150 kW, pump > 150 kW, hvac > 500 kW, plug > 50 kW, IT > 5,000 kW are invalid (99.99th percentiles: cooling 62, pump 65, hvac 216 kW) | cooling 54, hvac 1 reading |
| Complete minutes | A minute is kept only if all five components are valid | 39 rows had a missing component |
| Impossible PUE | Drop minutes where (sum of components / IT) is outside 1 to 3 | included in the 626 power minutes removed in total |
| Temperature | Keep -30 °F to 115 °F, then convert to °C with `(F - 32) * 5/9` | 1 reading (-39.4 °F) |
| Humidity | Keep values above 0 % and up to 100 %; exactly 0 % is a sensor dropout | 5,521 readings, mostly 2017-2019 |
| Hourly power | Mean of valid minutes; the hour is kept only with at least 45 of 60 minutes | |
| Hourly weather | Mean of valid readings; the hour is kept only with at least 20 readings. Weather was logged every 2 minutes in 2019, so a 45-reading rule would drop most of that year | |
| Grid | One row per hour from the first to the last power hour; hours that fail a rule stay as missing values so gaps remain visible | |
| Derived columns | `total_kw` = sum of the 5 components; `mechanical_kw` = cooling + pump + hvac | |

### Result (built on 2026-11-06)
- 80,759 hours from 2016-06-12 06:00 to 2025-08-29 04:00
- Power data in 72,282 hours (89.5 %), weather data in 71,747 hours (88.8 %)
- Annual PUE (ratio of sums):

| Year | PUE |
|---|---|
| 2016 (from June) | 1.0350 |
| 2017 | 1.0327 |
| 2018 | 1.0301 |
| 2019 | 1.0296 |
| 2020 | 1.0286 |
| 2021 | 1.0244 |
| 2022 | 1.0381 |
| 2023 | 1.0339 |
| 2024 | 1.0706 |
| 2025 (to August) | 1.0650 |
| All years | 1.0440 |

2016 to 2023 are within 0.012 of NLR's published annualised PUE of 1.036.
2024 and 2025 are clearly higher; the cause (a change at the facility or in
metering) is not stated in the dataset README.

## Attribution
Data cleaned and resampled by the authors for this study.

## Confirmed structure (inspected on 2026-11-04)

| File | Rows | Columns | Time range | Step between rows |
|---|---|---|---|---|
| esif.influx.buildingData.outside.combined.parquet | 4034917 | 6 | 2016-06-12 06:00:18 to 2025-08-29 18:51:19.790000 (plus one placeholder row dated 1970-01-01) | 0 days 00:01:00 |
| esif.influx.buildingData.PUE.combined.parquet | 4569543 | 11 | 2015-11-10 03:00:01 to 2025-08-29 04:35:08.461000 | 0 days 00:01:00 |

### Power metrics columns
| Column | Type | Unit | Meaning (from README) | Missing |
|---|---|---|---|---|
| tags | object | not stated | not stated | 4569543 |
| ts | datetime64[us] | not stated | Timestamp | 0 |
| cooling_kw | float64 | kilowatts | Cooling (kilowatts) - Captures the power used by fans and pipe trace heaters associated with outdoor cooling equipment. The dedicated tower filter pump power is also captured as cooling load. | 136502 |
| energy_reuse | float64 | unit unclear: values range -163 to 976 | Energy Reuse Effectiveness | 3562726 |
| ere | float64 | likely dimensionless (inferred from the name, not from the values) | not stated | 12 |
| hvac_kw | float64 | kilowatts | Heating, ventilation, and air conditioning (kilowatts) - Captures fan walls, fan coils that support the data center electrical rooms, and the make-up air unit. | 136510 |
| it_power_kw | float64 | kilowatts | IT equipment (kilowatts) - Captures power used by the IT equipment on the data center floor. | 136488 |
| plug_and_light_kw | float64 | kilowatts | Lights and utility plugs (kilowatts) - Captures power associated with the data center and dedicated mechanical room. The crank-case heater for the emergency standby generator is also captured as light and plug load. | 136486 |
| pue | float64 | likely dimensionless (inferred from the name, not from the values) | Power Usage Effectiveness | 799 |
| pump_kw | float64 | kilowatts | Pumps (kilowatts) - Captures power from pumps that move water in the data center Energy Recover Water loop and the Tower Water loops, and also captures power used by the boost pumps that circulate water through the fan walls. Note: The tower filter pump runs constantly to filter water from the data center cooling tower system, so 2.67 kilowatts are attributed to this pump and that is not reflected in this data field. | 136487 |
| day | int64 | not applicable (day number) | Day of month | 0 |

### Weather columns
| Column | Type | Unit | Meaning (from README) | Missing |
|---|---|---|---|---|
| tags | object | not stated | not stated | 4034917 |
| ts | datetime64[us] | not stated | Timestamp | 0 |
| outdoor_air_humidity | float64 | Relative humidity percent | Outside air humidity - Relative humidity percent (named `outside_air_humidity` in README) | 981 |
| outdoor_air_temp | float64 | Degrees Fahrenheit | Outside air temperature - Degrees Fahrenheit (named `outside_air_temp` in README) | 1077 |
| unit | str | not stated | not stated | 3306781 |
| day | int64 | not applicable (day number) | Day of month | 0 |

### Notes
- **Time zone of the timestamps**: Not stated in the README or inspect output (timestamps are stored as timezone-naive `datetime64[us]`).
- **How the README defines PUE and total facility power**: The README defines `pue` verbatim as `"Power Usage Effectiveness"` and does not define or mention total facility power ("not stated"). Total facility power does not exist in the raw data and is a HYPOTHESIS: `it_power_kw + cooling_kw + hvac_kw + plug_and_light_kw + pump_kw`. When tested against the raw `pue` column (`(sum / it_power_kw) - pue`), the median absolute difference is `0.00017637577322948683` and the 99th percentile absolute difference is `0.0004935372434500306`. Because the median absolute difference is below 0.005, the data is consistent with this hypothesis (this 0.005 threshold is a rule of thumb chosen by our team, not a standard). Regarding column overlap, the README explicitly notes under `pump_kw` that 2.67 kW for the dedicated tower filter pump is captured under `cooling_kw` ("The dedicated tower filter pump power is also captured as cooling load") and "is not reflected in this data field" (`pump_kw`), avoiding double-counting; none of the other power columns overlap.
- The README's linked NLR page (https://www.nlr.gov/computational-science/measuring-efficiency-pue) states that instantaneous PUE is calculated from five components: lights and plugs, cooling, pumps, HVAC and IT equipment. These are the five columns we sum for total_kw. All are metered except generator heat (calculated as a percentage of generator heat) and the tower filter pump (a fixed 2.67 kW is attributed). So the data is mostly measured, with two calculated components.
- NLR reports an annualised PUE of 1.036. After cleaning, our computed annual PUE should be compared with this value.
- We do not use the ere or energy_reuse columns. We compute PUE from the power columns and use the dataset's pue column only as a cross-check.
- **Potential confusion between ere and energy_reuse**: The columns `ere` and `energy_reuse` may be confused: the README defines `- energy_reuse:  Energy Reuse Effectiveness` and never mentions `ere` or `ERE`. In the raw Parquet file, however, `ere` has only 12 missing values while `energy_reuse` has 3,562,726 missing values (~78% missing). It is not stated which column corresponds to which definition in the data.
- **Identical minimum between pue and ere**: `pue` and `ere` share the identical minimum (-42.608), which suggests one bad reading event, not independent errors.
- **Sampling gaps and regular grid**: There are 34,170 gaps over 5 minutes in `pue` (largest: 12 days 21:11:12) and 20,414 gaps over 5 minutes in `weather` (largest: 36 days 02:10:45). "Step between rows: 1 minute" is the most common step, not a guarantee of a regular grid.
- **Anything odd (gaps, negative values, constant columns, where min equals max)**:
  - **Timestamp anomalies and gaps**:
    - In `esif.influx.buildingData.outside.combined.parquet`, the first record is timestamped `1970-01-01 00:00:00` (Unix epoch placeholder row with 0.0 humidity and 0.0 temperature), followed by a gap of over 46 years until `2016-06-12 06:00:18`.
    - In `esif.influx.buildingData.PUE.combined.parquet`: The first timestamp with all power columns present is `2016-06-12 06:00:18`. There are 136,484 rows before that timestamp (lacking power breakdown data), and 39 rows with gaps after that timestamp.
    - Timestamps contain fractional seconds (microseconds) with minor sampling jitter around the 1-minute step.
  - **Negative values**:
    - `cooling_kw` has negative values (min: `-3.33` kW).
    - `hvac_kw` has negative values (min: `-6.94` kW).
    - `pump_kw` has negative values (min: `-4.0` kW).
    - `pue` has negative values (min: `-42.608`), which is invalid.
    - `ere` has negative values (min: `-42.608`); negative values are invalid, but values below 1 can be legitimate.
    - `energy_reuse` has negative values (min: `-163.088904`).
  - **Extreme outliers**:
    - `outdoor_air_temp` reaches a minimum of `-39.400002` °F (-39.4 °F), which is an extreme value worth checking.
    - `pue` reaches a maximum of `528.300079` (mean is 1.04, 75th percentile is 1.047).
    - `ere` reaches a maximum of `547.392`.
    - `cooling_kw` reaches a maximum of `2516.37` kW (75th percentile is 15.87 kW).
    - `hvac_kw` reaches a maximum of `5071.570167` kW (75th percentile is 10.81 kW).
  - **Constant and all-missing columns**:
    - `tags` is 100% missing (count = 0, all null) in both files (4,569,543 in PUE, 4,034,917 in weather).
    - `unit` in weather has 3,306,781 missing values out of 4,034,917 rows; verification confirmed non-null values are `['outside']` (`<ArrowStringArray>`, Length: 1, dtype: str).
    - There are no columns where min equals max.
  - **Schema and naming discrepancies**:
    - Weather Parquet columns are named `outdoor_air_humidity` and `outdoor_air_temp`, whereas the README names them `outside_air_humidity` and `outside_air_temp`.
