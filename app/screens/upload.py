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
    "power": {"kW": "kW", "W": "W (watts)", "kWh": "kWh per reading"},
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

CSS = """
<style>
.block-container{max-width:1180px}
.up-chips{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 14px}
.up-chip{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:10px 14px;
  font-size:14px;color:#334155;flex:1 1 220px}
.up-chip b{display:block;color:#0F172A;font-size:15px}
.st-key-dropzone{background:linear-gradient(135deg,#ECFEFF,#EEF2FF);
  border:2px dashed #0891B2;border-radius:20px;padding:22px 24px 18px;min-height:256px}
.st-key-dropzone [data-testid="stFileUploaderDropzone"]{background:#FFFFFF;
  border:1px solid #C7D2FE;border-radius:14px;padding:34px 22px}
.st-key-dropzone [data-testid="stFileUploaderDropzone"] button{
  background:linear-gradient(120deg,#0891B2,#4338CA);color:#FFFFFF;border:0;font-weight:700}
.st-key-helper{background:#0F172A;border-radius:20px;padding:22px 22px 16px;min-height:256px}
.st-key-helper p,.st-key-helper span{color:#CBD5E1}
.helper-t{font-size:18px;font-weight:700;color:#FFFFFF !important;margin:0 0 4px}
.st-key-helper .stDownloadButton button{background:#22D3EE;color:#0F172A;border:0;
  font-weight:700;width:100%}
.st-key-helper .stDownloadButton button:hover{background:#67E8F9;color:#0F172A}
.st-key-helper .stDownloadButton button p{color:#0F172A !important;font-weight:700}
.st-key-helper .stDownloadButton,.st-key-helper .stDownloadButton button{width:100%}
.up-table{width:100%;border-collapse:collapse;font-size:14px}
.up-table th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.05em;
  color:#64748B;padding:8px 10px;border-bottom:1px solid #E2E8F0}
.up-table td{padding:8px 10px;border-bottom:1px solid #F1F5F9;color:#334155;vertical-align:top}
.up-table code{background:#ECFEFF;color:#0E7490;padding:2px 6px;border-radius:6px}
.req{background:#FEE2E2;color:#991B1B;font-size:11px;font-weight:700;padding:2px 8px;
  border-radius:999px}
.opt{background:#F1F5F9;color:#475569;font-size:11px;font-weight:700;padding:2px 8px;
  border-radius:999px}
.st-key-nextbar .stButton button{font-size:18px;padding:.8rem 1.6rem}
.st-key-nextbar .stButton button p{font-size:18px;font-weight:800}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

top_bar("upload")
st.markdown('<div class="cc-h">Upload your data</div>'
            '<div class="cc-lead">Drop in a file with your power readings. We check it, you '
            "confirm the columns, and you are ready for the questions.</div>"
            '<div class="up-chips">'
            '<div class="up-chip"><b>What the file needs</b>Date and time, IT power, and total '
            "facility power</div>"
            '<div class="up-chip"><b>File type</b>CSV or Excel (.xlsx), any column names and '
            "units</div>"
            '<div class="up-chip"><b>How much data</b>At least 1 month · 6+ months recommended'
            "</div>"
            '<div class="up-chip"><b>🔒 Private</b>Processed for this session only, deleted '
            "when you exit</div></div>", unsafe_allow_html=True)

drop, helper = st.columns([5, 2], gap="medium")
with drop:
    with st.container(key="dropzone"):
        st.markdown('<p class="cc-step-t"><span class="cc-num">1</span>Choose your file</p>',
                    unsafe_allow_html=True)
        uploaded = st.file_uploader("Drag a CSV or Excel file here, or click Upload",
                                    type=["csv", "xlsx"], key="file")
with helper:
    with st.container(key="helper"):
        st.markdown('<p class="helper-t">No file ready?</p>'
                    "<p>Start from our template, or try CoolCast with the example file.</p>",
                    unsafe_allow_html=True)
        st.download_button("Download template", template_csv(), "coolcast_template.csv",
                           "text/csv", key="dl_template")
        st.download_button("Download example file", example_csv(), "coolcast_example.csv",
                           "text/csv", key="dl_example")

if uploaded is None:
    rows = "".join(
        f"<tr><td><code>{r['Column']}</code></td><td>{r['What it means']}</td>"
        f"<td>{r['Unit']}</td><td><span class=\"{'req' if r['Required?'] == 'Required' else 'opt'}"
        f"\">{r['Required?']}</span></td></tr>" for _, r in TEMPLATE_COLUMNS.iterrows())
    with st.expander("Which columns can my file have?", expanded=True):
        st.markdown('<table class="up-table"><tr><th>Column in our template</th>'
                    "<th>What it means</th><th>Unit</th><th></th></tr>" + rows + "</table>",
                    unsafe_allow_html=True)
        st.caption("Your own column names are fine too: after you upload, we suggest which of "
                   "your columns is which and you confirm.")
    left, right = st.columns(2)
    with left.expander("File rules"):
        st.markdown(
            "- First row = column names. One row per timestamp, no repeated timestamps.\n"
            "- **Average power in kW**, not cumulative meter readings. If you have kWh per "
            "interval: kW = kWh ÷ interval in hours.\n"
            "- **Leave missing readings empty.** Do not write 0 or NA: a 0 looks like a real "
            "reading.\n"
            "- Plain numbers only: `1053.7`, not `1,053.7` or `1053 kW`.\n"
            "- CSV (comma-separated, UTF-8) or Excel .xlsx (first sheet), up to 200 MB.")
    with right.expander("Units we convert for you"):
        st.markdown(
            "- Power in **W or kW**, or energy as **kWh per reading**\n"
            "- Temperature in **°F or °C**\n"
            "- Humidity as **% or 0–1**\n"
            "- Dates written **day-first or month-first**\n"
            "- If there is no total column, we **add up the parts** (cooling, pumps, fans, "
            "lights, other)")
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

st.markdown('<p class="cc-step-t" style="margin-top:18px"><span class="cc-num">2</span>'
            "Check your columns</p>", unsafe_allow_html=True)
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

st.markdown('<p class="cc-step-t" style="margin-top:18px"><span class="cc-num">3</span>'
            "File check</p>", unsafe_allow_html=True)
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


with st.container(key="nextbar"):
    _, middle, _ = st.columns([1, 2, 1])
    middle.button("Continue to 10 questions →", key="next", type="primary",
                  disabled=level == "blocked", on_click=save_and_continue,
                  use_container_width=True)
