"""Upload screen: the user gives us their file, we check it, and they confirm the columns.

Reading, column matching, unit conversion and checks are done by src/upload.py
(#25). This screen shows them, lets the user correct the guesses, and stores
the clean hourly table for the next steps.
"""

import pandas as pd
import streamlit as st

from app.components import error_state, status_box
from app.state import go_to
from app.ui import top_bar
from src.upload import (
    UploadError,
    apply_mapping,
    check_length,
    example_csv,
    guess_units,
    read_file,
    suggest_mapping,
    template_csv,
)

NOT_USED = "(not used)"
NAMES = {
    "ts": "Date and time", "it_kw": "IT power", "total_kw": "Total facility power",
    "cooling_kw": "Cooling plant", "pump_kw": "Pumps", "hvac_kw": "Air handling / fans",
    "plug_kw": "Lights and plugs", "other_kw": "Other non-IT power",
    "temp_c": "Outdoor temperature", "humidity": "Outdoor humidity",
}
UNIT_CHOICES = {
    "power": {"kW": "kW (average power)", "W": "W (watts)", "kWh": "kWh per reading"},
    "temp_c": {"C": "°C", "F": "°F"},
    "humidity": {"pct": "% (0-100)", "fraction": "0-1"},
}
TEMPLATE_COLUMNS = pd.DataFrame([
    ("timestamp", "Start time of the reading, in your site's local time", "YYYY-MM-DD HH:MM",
     "Required"),
    ("it_kw", "Power used by IT equipment: servers, storage, network (usually at the UPS output)",
     "kW", "Required"),
    ("total_kw", "Total facility power from the main meter (or give the parts below and we add "
     "them)", "kW", "Required"),
    ("cooling_kw", "Cooling plant: chillers, cooling towers, dry coolers", "kW", "Optional"),
    ("pump_kw", "Pumps moving chilled or condenser water", "kW", "Optional"),
    ("hvac_kw", "Indoor air handling: CRAH/CRAC units, fan walls, air handlers", "kW", "Optional"),
    ("plug_kw", "Lights and small power in the data hall and support rooms", "kW", "Optional"),
    ("other_kw", "Other non-IT power: UPS and transformer losses, security, offices", "kW",
     "Optional"),
    ("temp_c", "Outdoor air temperature (if missing, we use past weather for your city)", "°C",
     "Optional"),
    ("humidity_pct", "Outdoor relative humidity (if missing, we use past weather for your city)",
     "% (0-100)", "Optional"),
], columns=["Column", "What it means", "Unit", "Required?"])


def check_line(ok: str, text: str) -> None:
    """One line of the file check list: ok is "good", "check" or "problem"."""
    icon = {"good": "✅", "check": "⚠️", "problem": "❌"}[ok]
    st.markdown(f"{icon} {text}")


def unit_kind(std: str) -> str:
    return std if std in ("temp_c", "humidity") else "power"


# ---------------------------------------------------------------- top

top_bar("upload")
st.title("Upload your data")
st.caption("🔒 Your file is processed in memory for this session only and deleted when you exit. "
           "Only your city's name is sent anywhere, later, to look up public weather.")

template, as_is = st.columns(2, gap="large")
with template:
    with st.container(border=True):
        st.subheader("Use our template")
        st.dataframe(TEMPLATE_COLUMNS, hide_index=True)
        st.markdown(
            "**File rules**\n"
            "- First row = column names. One row per timestamp, no repeated timestamps.\n"
            "- **Average power in kW**, not cumulative meter readings. If you have kWh per "
            "interval: kW = kWh ÷ interval in hours.\n"
            "- **Leave missing readings empty.** Do not write 0 or NA: a 0 looks like a real "
            "reading.\n"
            "- Plain numbers only: `1053.7`, not `1,053.7` or `1053 kW`.\n"
            "- CSV (comma-separated, UTF-8) or Excel .xlsx (first sheet), up to 200 MB.")
        a, b = st.columns(2)
        a.download_button("Download template (CSV)", template_csv(), "coolcast_template.csv",
                          "text/csv", key="dl_template")
        b.download_button("Download example file", example_csv(), "coolcast_example.csv",
                          "text/csv", key="dl_example")
with as_is:
    with st.container(border=True):
        st.subheader("Upload your file as it is")
        st.markdown(
            "Any column names and units are fine. After uploading, we suggest which of your "
            "columns is which, and you confirm.\n\n"
            "- **Required:** a date-and-time column, IT power, and total facility power (or its "
            "parts: cooling, pumps, fans, lights…).\n"
            "- **Units we convert for you:** W or kW, kWh per interval, °F or °C, humidity as % "
            "or 0–1, day-first or month-first dates.\n"
            "- **Optional:** separate cooling, pump, fan, lighting columns and outdoor "
            "temperature or humidity.\n"
            "- At least **1 month** of data is needed; **6+ months** is recommended and "
            "**12+ months** gives the best results.")

uploaded = st.file_uploader("Drag a CSV or Excel file here", type=["csv", "xlsx"], key="file")
if uploaded is None:
    st.stop()

# ---------------------------------------------------------------- reading

if st.session_state.get("raw_id") != uploaded.file_id:
    try:
        raw = read_file(uploaded)
    except UploadError as err:
        error_state(str(err))
        st.stop()
    st.session_state["raw"] = raw
    st.session_state["raw_id"] = uploaded.file_id
    st.session_state["mapping"] = {c: std for c, (std, _) in suggest_mapping(raw).items()}
    st.session_state["units"] = guess_units(raw, st.session_state["mapping"])
raw: pd.DataFrame = st.session_state["raw"]

# ---------------------------------------------------------------- column confirm

st.subheader("Check your columns")
st.caption("We guessed which of your columns is which. Change anything that is wrong.")
choices = [NOT_USED, *NAMES]
mapping = {}
units = dict(st.session_state["units"])
header = st.columns([3, 3, 3, 2])
for col, title in zip(header, ["Your column", "First values", "Is", "Unit"]):
    col.markdown(f"**{title}**")
for i, column in enumerate(raw.columns):
    name, sample, chosen, unit = st.columns([3, 3, 3, 2], vertical_alignment="center")
    name.write(column)
    sample.caption(", ".join(str(v) for v in raw[column].dropna().head(3)) or "(empty)")
    guess = st.session_state["mapping"].get(column)
    pick = chosen.selectbox(column, choices, index=choices.index(guess) if guess else 0,
                            format_func=lambda c: NAMES.get(c, c), key=f"map_{i}",
                            label_visibility="collapsed")
    mapping[column] = None if pick == NOT_USED else pick
    if mapping[column] and mapping[column] != "ts":
        options = UNIT_CHOICES[unit_kind(mapping[column])]
        current = units.get(mapping[column], next(iter(options)))
        units[mapping[column]] = unit.selectbox(
            f"Unit of {column}", list(options), index=list(options).index(current),
            format_func=options.get, key=f"unit_{i}", label_visibility="collapsed")

options = {"units": units}
try:
    table, report = apply_mapping(raw, mapping, options)
except UploadError as err:
    if "ambiguous" not in str(err):
        error_state(str(err))
        st.stop()
    order = st.radio("Your dates are ambiguous. How are they written?",
                     ["Day first (31/01/2024)", "Month first (01/31/2024)"], key="dayfirst",
                     horizontal=True, index=None)
    if order is None:
        st.stop()
    options["dayfirst"] = order.startswith("Day")
    try:
        table, report = apply_mapping(raw, mapping, options)
    except UploadError as err2:
        error_state(str(err2))
        st.stop()

# ---------------------------------------------------------------- checks

st.subheader("File check")
length = check_length(table)
check_line("good", f"{report['rows_read']:,} rows read")
check_line("good", f"Dates {report['start']:%d %b %Y} to {report['end']:%d %b %Y} "
                   f"({length['days']:,.0f} days), one reading every "
                   f"{report['interval_minutes']} minutes")
check_line("good", "Required columns found: date and time, IT power, total facility power")
optional = [NAMES[c] for c in report["columns"] if c in NAMES and c not in ("it_kw", "total_kw")]
check_line("good" if optional else "check",
           f"Optional columns: {', '.join(optional)}" if optional else
           "No optional columns: cooling and weather results will be limited")
bad = report["faulty_readings"] + report["rows_bad_time"]
check_line("good" if bad == 0 else "check", f"{bad:,} faulty readings removed"
           + ("" if not report["rows_bad_time"] else
              f" (including {report['rows_bad_time']:,} unreadable dates)"))
check_line("good" if report["duplicates_removed"] == 0 else "check",
           f"{report['duplicates_removed']:,} repeated timestamps removed")
gap_share = report["missing_hours"] / report["hours"] if report["hours"] else 1
check_line("good" if gap_share < 0.02 else "check" if gap_share < 0.25 else "problem",
           f"{report['missing_hours']:,} of {report['hours']:,} hours missing "
           f"({gap_share:.0%}); gaps are left empty, never filled with 0")

level = length["level"]
if level == "blocked":
    status_box("problem", length["message"])
elif level == "limited":
    status_box("check", f"Limited data: {length['message']}")
else:
    status_box("good", length["message"])


def save_and_continue() -> None:
    st.session_state["data"] = table
    st.session_state["file_name"] = uploaded.name
    st.session_state["upload_report"] = report
    st.session_state["data_level"] = level
    go_to("questions")


st.button("Continue to 10 questions →", key="next", type="primary",
          disabled=level == "blocked", on_click=save_and_continue)
