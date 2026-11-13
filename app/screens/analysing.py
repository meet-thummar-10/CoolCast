"""Analysing screen: runs the analysis and shows each step as it finishes."""

import random

import streamlit as st

from app.components import error_state
from app.pipeline import FACTS, STEPS, run_analysis
from app.state import go_to
from app.ui import top_bar

ICONS = {"waiting": "⏳", "running": "🔄", "done": "✅", "warning": "⚠️"}

top_bar("analysing")
st.title("Analysing your data")

data = st.session_state.get("data")
answers = st.session_state.get("answers") or {}
if data is None or not answers.get("price"):
    error_state("Your file or your answers are missing. Please start again from the upload step.")
    st.button("Go to upload", key="restart", on_click=go_to, args=("upload",))
    st.stop()

# Run once per file and set of answers; a rerun just shows the finished steps.
signature = (st.session_state.get("file_name"),
             repr(sorted((k, v) for k, v in answers.items() if k != "emission_factor")))
results = st.session_state.get("results") or {}
if results.get("signature") != signature:
    st.caption("This usually takes a few seconds. Please keep this page open.")
    progress = st.progress(0.0, text="Starting…")
    rows = [st.empty() for _ in STEPS]
    states = {i: ("waiting", "") for i in range(len(STEPS))}

    def show(i: int) -> None:
        status, detail = states[i]
        text = f"{ICONS[status]} **{STEPS[i]}**" + (f"  \n{detail}" if detail else "")
        rows[i].markdown(text)

    for i in states:
        show(i)
    st.info(f"**Did you know?** {random.choice(FACTS)}", icon=":material/lightbulb:")

    def report(step: int, status: str, detail: str) -> None:
        states[step] = (status, detail)
        show(step)
        finished = sum(s in ("done", "warning") for s, _ in states.values())
        progress.progress(finished / len(STEPS), text=f"{finished} of {len(STEPS)} steps done")

    try:
        results = run_analysis(data, answers, st.session_state.get("upload_report"),
                               st.session_state.get("file_name"), report=report)
    except ValueError as err:
        error_state(f"The analysis could not finish: {err}")
        st.button("Change my answers", key="back_to_questions", on_click=go_to,
                  args=("questions",))
        st.stop()
    results["signature"] = signature
    results["step_log"] = dict(states)
    st.session_state["results"] = results
    st.session_state["data"] = results.pop("table")
    answers["emission_factor"] = results["location"].get("emission_factor")
else:
    st.progress(1.0, text=f"{len(STEPS)} of {len(STEPS)} steps done")
    for i, name in enumerate(STEPS):
        status, detail = results.get("step_log", {}).get(i, ("done", ""))
        st.markdown(f"{ICONS[status]} **{name}**" + (f"  \n{detail}" if detail else ""))

st.success("Your analysis is ready.")
st.button("Open my analysis →", key="next", type="primary", on_click=go_to, args=("analysis",))
