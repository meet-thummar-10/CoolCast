"""10 Export: download the whole analysis before exiting (the data is deleted on exit)."""

import pandas as pd
import streamlit as st

from app.page_utils import page_start, table
from src.export import _sheets, build_excel, build_pdf

results = page_start("Export", "Take your results with you. Every file says whether each number "
                               "is measured, modelled, assumed or an estimate. Your data is "
                               "deleted when you exit, so download what you need first.")
stem = (results.get("file_name") or "coolcast").rsplit(".", 1)[0]

pdf_col, xlsx_col = st.columns(2)
with pdf_col:
    with st.container(border=True):
        st.subheader("Full report (PDF)")
        st.caption("Summary, key numbers, charts, every step to cut cost with its range, warning "
                   "and sources, benchmark, anomalies, forecast accuracy, your answers, data "
                   "quality and method notes.")
        st.download_button("Download PDF report", build_pdf(results),
                           f"{stem}_coolcast_report.pdf", "application/pdf", key="dl_pdf",
                           type="primary")
with xlsx_col:
    with st.container(border=True):
        st.subheader("Excel workbook")
        st.caption("One sheet per analysis: summary, monthly, anomalies, steps to cut cost, "
                   "forecast, your answers and settings, data quality.")
        st.download_button("Download Excel (.xlsx)", build_excel(results),
                           f"{stem}_coolcast.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="dl_xlsx", type="primary")

st.subheader("Individual tables (CSV)")
sheets = _sheets(results)
fc = results.get("forecast")
csvs = {
    "Summary of key numbers": ("summary", sheets["Summary"]),
    "Clean hourly data": ("hourly_data", table().assign(label="measured")),
    "Flagged anomalies": ("anomalies", sheets["Anomalies"]),
    "Steps to reduce your cost": ("steps_to_reduce_cost", sheets["Steps to reduce cost"]),
    "Forecast": ("forecast", fc["predictions"].assign(label="modelled") if fc is not None
                 else pd.DataFrame(columns=["ts", "actual", "label"])),
    "Your answers and settings": ("answers_and_settings", sheets["Your answers and settings"]),
}
for name, (slug, frame) in csvs.items():
    left, right = st.columns([4, 1], vertical_alignment="center")
    left.markdown(f"**{name}**  \n<small>{len(frame):,} rows</small>", unsafe_allow_html=True)
    right.download_button("Download CSV", frame.to_csv(index=False).encode("utf-8"),
                          f"{stem}_{slug}.csv", "text/csv", key=f"dl_{slug}")
