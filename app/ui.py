"""Layout pieces shared by the screens: logo, top bar, sidebar and styles."""

from pathlib import Path

import streamlit as st

from app.state import exit_analysis, go_to

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "logo.svg"
LOGO_SVG = LOGO.read_text(encoding="utf-8")
STEPS = (("upload", "Upload"), ("questions", "Questions"), ("analysing", "Analysis"))

CSS = """
<style>
.cc-brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:22px;color:#0F172A}
.cc-brand svg{width:30px;height:30px;stroke:#0891B2}
.cc-steps{display:flex;gap:18px;flex-wrap:wrap;font-size:14px;color:#64748B}
.cc-steps .on{color:#0F172A;font-weight:600}
.cc-steps .done{color:#0891B2}
.cc-hero h1{font-size:46px;line-height:1.1;margin:0}
.cc-card{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:20px;height:100%}
.cc-card b{display:block;font-size:17px;margin-bottom:6px}
.cc-muted{color:#475569}
.st-key-exit button{background:#FEF2F2;color:#991B1B;border:1px solid #FECACA;width:100%}
.st-key-exit button:hover{background:#FEE2E2;color:#7F1D1D;border-color:#FCA5A5}
</style>
"""


def styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def brand() -> None:
    st.markdown(f'<div class="cc-brand">{LOGO_SVG}CoolCast</div>', unsafe_allow_html=True)


def top_bar(current: str | None = None) -> None:
    """Logo, the 3 steps (when inside the flow) and a Cancel link back to the landing page."""
    left, middle, right = st.columns([2, 4, 1], vertical_alignment="center")
    with left:
        brand()
    if current:
        names = [s for s, _ in STEPS]
        here = names.index(current)
        parts = []
        for i, (_, label) in enumerate(STEPS):
            cls = "on" if i == here else "done" if i < here else ""
            parts.append(f'<span class="{cls}">{"✓" if i < here else i + 1} {label}</span>')
        with middle:
            st.markdown(f'<div class="cc-steps">{"".join(parts)}</div>', unsafe_allow_html=True)
        with right:
            st.button("Cancel", key="cancel", on_click=exit_analysis, type="tertiary")
    st.divider()


def sidebar() -> None:
    """Sidebar for the analysis stage: your data, settings and Exit."""
    s = st.session_state
    answers = s.get("answers") or {}
    with st.sidebar:
        with st.container(border=True):
            st.caption("YOUR DATA")
            st.markdown(f"**{s.get('file_name') or 'No file yet'}**")
            info = (s.get("results") or {}).get("period")
            if info:
                st.caption(info)
            st.button("Upload a different file", key="new_file", on_click=go_to, args=("upload",),
                      type="tertiary")
        st.subheader("Settings")
        currency = answers.get("currency") or "–"
        st.caption(f"Currency: **{currency}** · set from your location")
        st.number_input(f"Electricity price ({currency}/kWh)", key="tariff", min_value=0.0,
                        value=float(answers.get("price") or 0.0), step=0.5)
        st.number_input("Grid emission factor (kg CO₂/kWh)", key="emission_factor",
                        min_value=0.0, value=float(answers.get("emission_factor") or 0.0),
                        step=0.001, format="%.3f")
        st.button("Change my answers", key="change_answers", on_click=go_to,
                  args=("questions",), type="tertiary")
        st.divider()
        st.button("Exit analysis", key="exit", icon=":material/logout:", on_click=exit_analysis)
        st.caption("Your data is deleted when you exit. Download the report first if you need it.")
