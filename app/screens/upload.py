"""Upload screen (content: issue #31)."""

import streamlit as st

from app.state import go_to
from app.ui import top_bar

top_bar("upload")
st.title("Upload your data")
st.info("Coming in issue #31: template, upload as it is, column check and data-length check.")
st.button("Continue to 10 questions →", key="next", type="primary", on_click=go_to,
          args=("questions",))
