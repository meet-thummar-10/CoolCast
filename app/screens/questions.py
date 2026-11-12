"""Questions screen (content: issue #32)."""

import streamlit as st

from app.state import go_to
from app.ui import top_bar

top_bar("questions")
st.title("About your site")
st.info("Coming in issue #32: 10 questions, one per screen, with a review screen.")
st.button("Analyse my data →", key="next", type="primary", on_click=go_to, args=("analysing",))
