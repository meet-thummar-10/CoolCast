"""1 Data: what the user's file contains and how complete it is."""

import pandas as pd
import streamlit as st

from app.components import bar_chart, kpi_card, status_box
from app.formatting import fmt_pct
from app.page_utils import page_start, table

COLUMN_MEANING = {
    "ts": ("Date and time", "Start of each hour, in your site's local time"),
    "it_kw": ("IT power", "Servers, storage and network (usually at the UPS output)"),
    "total_kw": ("Total facility power", "Everything on the site's main meter"),
    "cooling_kw": ("Cooling plant", "Chillers, cooling towers, dry coolers"),
    "pump_kw": ("Pumps", "Pumps moving chilled or condenser water"),
    "hvac_kw": ("Air handling / fans", "CRAH/CRAC units, fan walls, air handlers"),
    "plug_kw": ("Lights and plugs", "Lighting and small power"),
    "other_kw": ("Other non-IT power", "UPS and transformer losses, security, offices"),
    "mechanical_kw": ("Cooling system", "Cooling plant + pumps + air handling (added up by us)"),
    "temp_c": ("Outdoor temperature", "°C, from your file or past weather for your city"),
    "humidity": ("Outdoor humidity", "%, from your file or past weather for your city"),
}

results = page_start("Data", "What your file contains and how complete it is. Every other page "
                             "uses this cleaned table.")
df = table()
quality = results["quality"]

if st.session_state.get("data_level") == "limited":
    status_box("check", "Limited data: your file covers less than 6 months, so results are less "
                        "accurate than with 6+ months.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Quality grade", quality["grade"], "measured",
             help="A: 98 %+ of hours complete, B: 90 %+, C: 75 %+, D: below 75 %")
with c2:
    kpi_card("Hours complete", fmt_pct(quality["completeness"]), "measured")
with c3:
    kpi_card("Missing hours", f"{quality['missing_hours']:,}", "measured")
with c4:
    kpi_card("Longest gap", f"{quality['longest_gap_h']:,} hours", "measured")

report = st.session_state.get("upload_report") or {}
if report:
    removed = report.get("faulty_readings", 0) + report.get("rows_bad_time", 0)
    st.caption(f"Cleaning: {report.get('rows_read', len(df)):,} rows read, {removed:,} faulty "
               f"readings removed, {report.get('duplicates_removed', 0):,} repeated timestamps "
               "removed. Gaps are left empty, never filled with 0.")

complete = df[["it_kw", "total_kw"]].notna().all(axis=1)
coverage = (complete.groupby(df["ts"].dt.to_period("M")).mean() * 100).rename("it_kw")
coverage = coverage.reset_index().rename(columns={"ts": "Month"})
coverage["Month"] = coverage["Month"].astype(str)
bar_chart(coverage, "Month", "it_kw", title="Hours with complete data, by month",
          y_label="% of hours")

st.subheader("Data preview")
st.dataframe(df.head(48), hide_index=True)

st.subheader("What the columns mean")
rows = [(col, *COLUMN_MEANING[col]) for col in df.columns if col in COLUMN_MEANING]
st.dataframe(pd.DataFrame(rows, columns=["Column", "Name", "What it means"]), hide_index=True)
