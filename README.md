# CoolCast
**Green AI for Data-Centre Energy Efficiency**

CoolCast analyses data-centre power and weather data, forecasts cooling
energy with machine learning, and measures what each model costs in
energy, so you can see whether AI saves more energy than it uses.

## What it does
- Calculates standard efficiency metrics (PUE, cooling share, CUE)
- Forecasts cooling power and flags periods worth investigating
- Reports the training and inference energy of every model
- Recommends the lightest model that is accurate enough
- Estimates net energy, cost and CO2 savings under stated assumptions

## Quick start
```bash
git clone https://github.com/meet-thummar-10/CoolCast.git
cd CoolCast
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
pytest
streamlit run app/Home.py   # available once the app shell is merged
```

## Data
NLR HPC Facility Power Usage Effectiveness (PUE) Data, National
Laboratory of the Rockies, licensed CC BY 4.0
(https://data.nlr.gov/submissions/300). The raw files are not stored in
this repository. Download them into `data/raw/` (see `docs/data.md`), then
run `python scripts/inspect_data.py` to check them.
Data was cleaned and resampled by the authors.

## Project structure
```
app/        Streamlit pages (frontend)
src/        Data loading, metrics, models, energy measurement (backend)
tests/      Automated tests
docs/       Data notes, interface contract, team
scripts/    Helper scripts
data/demo/  Small demo data only (raw data stays in data/raw/, not in git)
```

## How to read the results
Each number in the app is tagged as **measured** (from data or our
benchmarks), **modelled** (from a model on measured data) or **assumed**
(a user or team input).

## Limitations
- Research prototype built on recorded open data. It does not control
  any cooling system, so savings figures are scenarios, not proof.
- Energy measurements are made on laptops and are estimates.
- Results come from one HPC facility and may not transfer to other sites.

## Team
See `docs/team.md`.

## Licence
Code: MIT (see `LICENSE`). Data: CC BY 4.0, attributed above.
