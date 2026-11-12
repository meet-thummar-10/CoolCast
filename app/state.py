"""Session state shared by every screen and page.

Stages, in order: landing -> upload -> questions -> analysing -> analysis.
Keys used by other issues: stage, data, file_name, answers, results.
"""

import streamlit as st

STAGES = ("landing", "upload", "questions", "analysing", "analysis")
DEFAULTS = {"stage": "landing", "data": None, "file_name": None, "answers": {}, "results": {}}


def init_state() -> None:
    """Fill in any missing key with its default."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value


def go_to(stage: str) -> None:
    """Move to another stage (use as a button ``on_click``, or call then ``st.rerun()``)."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {', '.join(STAGES)}, got {stage!r}")
    st.session_state["stage"] = stage


def exit_analysis() -> None:
    """Delete the user's data and answers and return to the landing page."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()
