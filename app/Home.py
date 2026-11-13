"""CoolCast entry point: `streamlit run app/Home.py`.

Before the analysis there is no sidebar: landing -> upload -> questions ->
analysing. After it, the sidebar shows the 11 analysis pages and Exit.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.state import init_state  # noqa: E402
from app.ui import LOGO, sidebar, styles  # noqa: E402

HERE = Path(__file__).resolve().parent

SCREENS = {
    "landing": ("screens/landing.py", "CoolCast"),
    "upload": ("screens/upload.py", "Upload your data"),
    "questions": ("screens/questions.py", "About your site"),
    "analysing": ("screens/analysing.py", "Analysing"),
}

ANALYSIS_PAGES = [
    ("1_Data.py", "Data", ":material/table_chart:"),
    ("2_Energy_and_Cost.py", "Energy & Cost", ":material/bolt:"),
    ("3_Efficiency_and_Load.py", "Efficiency & Load", ":material/speed:"),
    ("4_Cooling_and_Weather.py", "Cooling & Weather", ":material/ac_unit:"),
    ("5_Anomalies.py", "Anomalies", ":material/warning:"),
    ("6_Forecast_and_Planning.py", "Forecast & Planning", ":material/trending_up:"),
    ("7_How_to_reduce_your_cost.py", "How to reduce your cost", ":material/savings:"),
    ("8_Savings_calculator.py", "Savings calculator", ":material/calculate:"),
    ("9_Benchmark.py", "Benchmark", ":material/leaderboard:"),
    ("10_Export.py", "Export", ":material/download:"),
    ("11_Replay.py", "Replay", ":material/replay:"),
]


def main() -> None:
    st.set_page_config(page_title="CoolCast", page_icon=str(LOGO), layout="wide")
    init_state()
    styles()
    stage = st.session_state["stage"]
    if stage == "analysis":
        st.logo(str(LOGO), size="large")
        pages = [st.Page(str(HERE / "pages" / f), title=t, icon=i) for f, t, i in ANALYSIS_PAGES]
        nav = st.navigation(pages, position="sidebar")
        sidebar()
    else:
        path, title = SCREENS[stage]
        nav = st.navigation([st.Page(str(HERE / path), title=title)], position="hidden")
    nav.run()


main()
