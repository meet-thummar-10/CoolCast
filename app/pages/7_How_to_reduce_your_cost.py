"""7 How to reduce your cost: steps that fit the site, each with a careful, sourced range."""

import streamlit as st

from app.components import tag_html
from app.page_utils import co2_range, energy_range, money_range, page_start

EFFORT = {"free": "Free: a setting or process change", "small": "Small investment",
          "large": "Larger project"}
FILTERS = {"free": ("Free changes only", {"free"}),
           "small": ("Free + small investments", {"free", "small"}),
           "large": ("All steps", {"free", "small", "large"})}

results = page_start("How to reduce your cost",
                     "Steps that fit your site, based on your data and your 10 answers. Each "
                     "saving is a careful range from published studies, applied only to the part "
                     "of your energy it affects.")
st.info("**How to read these savings:** they are **estimates, not promises**. The low end can "
        "be zero if equipment is already optimised. Steps overlap, so **do not add the ranges "
        "together**. Confirm any change with your engineer or supplier before acting.",
        icon=":material/info:")

answers = st.session_state.get("answers") or {}
default = answers.get("can_change") or "large"
choice = st.radio("Show", list(FILTERS), index=list(FILTERS).index(default),
                  format_func=lambda k: FILTERS[k][0], horizontal=True, key="effort_filter")
st.caption("Preset from your answer to \"What kind of changes can you make?\"")

steps = results["steps"]["steps"]
shown = [s for s in steps if s["effort"] in FILTERS[choice][1]]
for n, s in enumerate(shown, 1):
    with st.container(border=True):
        st.markdown(f"#### {n}. {s['title']}")
        st.caption(f"{EFFORT[s['effort']]} · Confidence: {s['confidence']}")
        left, right = st.columns(2)
        left.markdown(f"**What we found**  \n{s['found']}")
        right.markdown(f"**What to do**  \n{s['todo']}")
        if s["low_kwh"] is not None:
            per = f" per {s['per']}" if s["per"] else ""
            e, m, c = st.columns(3)
            e.metric(f"Energy{per}", energy_range(s["low_kwh"], s["high_kwh"]))
            m.metric(f"Money{per}", money_range(s["low_money"], s["high_money"]))
            if s["low_co2_kg"] is not None:
                c.metric(f"CO₂{per}", co2_range(s["low_co2_kg"], s["high_co2_kg"]))
        st.caption(f"**How it is calculated:** {s['calc']}")
        st.warning(f"**Before you act:** {s['warning']}")
        st.markdown(f"<small>**Sources:** {s['sources']} {tag_html('estimate')}</small>",
                    unsafe_allow_html=True)

hidden = len(steps) - len(shown)
if hidden:
    st.caption(f"{hidden} more step{'s are' if hidden > 1 else ' is'} hidden by the filter above. "
               "Choose \"All steps\" to see them.")
skipped = results["steps"]["skipped"]
if skipped:
    with st.expander(f"Steps not shown for your site ({len(skipped)})"):
        for s in skipped:
            st.markdown(f"- **{s['id'].replace('_', ' ').capitalize()}**: {s['reason']}")
st.caption("Savings are for the period covered by your data.")
