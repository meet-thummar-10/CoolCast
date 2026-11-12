"""Analysing screen (content: issue #32)."""

import streamlit as st

from app.state import go_to
from app.ui import top_bar

top_bar("analysing")
st.title("Analysing your data")
st.info("Coming in issue #32: live steps while the analysis runs.")
st.button("Open my analysis →", key="next", type="primary", on_click=go_to, args=("analysis",))
