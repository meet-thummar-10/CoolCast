"""Landing page: what CoolCast does, and the Upload button."""

import streamlit as st

from app.state import go_to
from app.ui import brand

left, right = st.columns([5, 2], vertical_alignment="center")
with left:
    brand()
with right:
    st.button("Upload your data", key="upload_top", type="primary", on_click=go_to,
              args=("upload",), use_container_width=True)
st.divider()

hero, example = st.columns([3, 2], gap="large", vertical_alignment="center")
with hero:
    st.markdown('<div class="cc-hero"><h1>Find where your data centre wastes energy</h1></div>',
                unsafe_allow_html=True)
    st.markdown(
        '<p class="cc-muted" style="font-size:18px">Upload your power data, answer 10 short '
        "questions, and see where energy and money go, how you compare with published global "
        "figures, and which changes could lower your bill, each with a careful, sourced "
        "range.</p>", unsafe_allow_html=True)
    st.button("Upload your data →", key="upload_hero", type="primary", on_click=go_to,
              args=("upload",))
    st.caption("Free · works for any country · your file is deleted when you exit")
with example:
    with st.container(border=True):
        st.caption("EXAMPLE RESULT")
        a, b = st.columns(2)
        a.metric("PUE", "1.034", help="Global average 1.52 (Uptime Institute 2026)")
        b.metric("Overhead always on", "83%")
        a.metric("Free-cooling hours", "6,460 / yr")
        b.metric("Top step (MWh a year)", "55 – 110")

st.header("How it works")
steps = st.columns(3)
for col, (title, text) in zip(steps, [
    ("1. Upload your data", "A CSV or Excel file with hourly IT and total power. Use our "
     "template, or upload your file as it is and confirm the columns."),
    ("2. Answer 10 questions", "Your location and electricity price, then a few optional "
     "questions about your cooling, UPS and plans. \"I don't know\" is always fine."),
    ("3. Get your analysis", "We clean the data, add past local weather and your grid's CO₂, "
     "and show where to save, with ranges and sources."),
]):
    col.markdown(f'<div class="cc-card"><b>{title}</b><span class="cc-muted">{text}</span></div>',
                 unsafe_allow_html=True)

st.header("What you get")
features = [
    ("Energy & Cost", "PUE, overhead, cost and CO₂ in your currency"),
    ("Efficiency & Load", "How efficient you are at every IT load"),
    ("Cooling & Weather", "Free-cooling hours from your local weather"),
    ("Anomalies", "Periods that used more energy than expected"),
    ("How to reduce your cost", "Steps that fit your site, with sourced ranges"),
    ("Benchmark & Export", "Compare globally; download PDF and Excel"),
]
for row in range(0, len(features), 3):
    cols = st.columns(3)
    for col, (title, text) in zip(cols, features[row:row + 3]):
        col.markdown(f'<div class="cc-card"><b>{title}</b><span class="cc-muted">{text}'
                     "</span></div>", unsafe_allow_html=True)

st.header("Privacy & accuracy")
st.markdown(
    "- Your file is processed in memory for your session only and **deleted when you exit**.\n"
    "- Only your city's coordinates are used to look up public weather and grid data.\n"
    "- Every number is labelled **measured**, **modelled** or **assumed**; savings are "
    "**estimates shown as ranges**, never added together.")
st.divider()
st.caption("CoolCast · open-source data-centre energy analysis")
