# CoolCast
**Find where your data centre wastes energy, and how to cut its cost.**

CoolCast is a free analysis tool for data-centre operators anywhere in the
world. You upload your own power data, answer 10 short questions about
your site, and CoolCast shows where energy and money go, how your site
compares with published global figures, and which changes could lower your
bill, each with a careful, sourced saving range.

## How it works
1. **Upload your data.** A CSV or Excel file with hourly (or finer)
   readings. Use our template, or upload your file as it is and confirm
   which column is which. At least 1 month is needed; 6+ months is
   recommended and 12+ months gives the best results.
2. **Answer 10 questions.** Your location (required) and electricity price
   from your bill (required), then optional questions about your cooling,
   setpoint, drives, UPS and what changes you can make. "I don't know"
   is always allowed and leads to a cautious assumption.
3. **Get your analysis.** CoolCast cleans the data, fetches past local
   weather, your grid's CO2 factor and carbon price, and builds the report.

## What you get
- **Data:** quality grade, gaps and faulty readings removed
- **Energy & Cost:** PUE, overhead energy, cost and CO2 in your currency
- **Efficiency & Load:** PUE at different IT loads; how much overhead is
  always on, follows the servers or follows the weather
- **Cooling & Weather:** free-cooling hours from your local past weather
- **Anomalies:** periods that used more energy than expected
- **Forecast & Planning:** predicted energy for the coming weeks
- **How to reduce your cost:** steps that fit your site, each with what we
  found, what to do, a saving range, confidence, effort, warnings and sources
- **Savings calculator:** try your own "what if" with low and high guesses
- **Benchmark:** your PUE against published global figures
- **Export:** PDF report, Excel workbook and CSV tables

## How to read the results
Every number is labelled **measured** (from your file), **modelled** (from
a model on your data) or **assumed** (from your answers or a published
source). Savings are **estimates, shown as ranges, never added together**.
The low end can be zero if equipment is already optimised. Confirm any
change with your engineer or supplier before acting.

## Privacy
Your file is processed in memory for your session only and is deleted when
you exit the analysis. Only your city's coordinates are used to look up
public weather and grid data. Nothing is sent to an AI service.

## Quick start (developers)
```bash
git clone https://github.com/meet-thummar-10/CoolCast.git
cd CoolCast
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
pytest
streamlit run app/Home.py
```

## Development data
To build and test CoolCast we use the NLR HPC Facility Power Usage
Effectiveness (PUE) Data, National Laboratory of the Rockies, licensed
CC BY 4.0 (https://data.nlr.gov/submissions/300). It is used internally
for development and tests only and is **never shown to users**. The raw
files are not stored here; see `docs/data.md`. Data was cleaned and
resampled by the authors.

## Project structure
```
app/        Streamlit pages (frontend)
src/        Upload, cleaning, metrics, forecasts, recommendations (backend)
tests/      Automated tests
docs/       Data notes, interface contract, assumptions, team
scripts/    Helper scripts
data/demo/  Small development sample (raw data stays in data/raw/, not in git)
```

## Limitations
- CoolCast analyses recorded data. It does not control any equipment.
- Saving ranges come from published studies and your answers; real savings
  depend on your building and need an engineer's assessment.
- Results are only as good as the uploaded data; less than 6 months of
  data gives less accurate results.

## Team
See `docs/team.md`.

## Licence
Code: MIT (see `LICENSE`). Development data: CC BY 4.0, attributed above.
