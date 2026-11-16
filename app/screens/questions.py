"""Questions screen: 10 questions, one per screen, then a review screen.

Answers go to st.session_state["answers"] (keys in app/questions.py).
Question 1 (location) and 2 (electricity price) are required; the others
accept "I don't know", which leads to a cautious assumption.
"""

import streamlit as st

from app.components import status_box
from app.formatting import CURRENCIES
from app.questions import IDK, QUESTIONS, TOTAL, answer_text, answered_count, is_answered
from app.state import go_to
from app.ui import top_bar
from src.location import country_names, find_country, load_countries
from src.recommend import OPTIONS

REVIEW = TOTAL  # index of the review screen
answers: dict = st.session_state.setdefault("answers", {})
if "q_index" not in st.session_state:
    st.session_state["q_index"] = REVIEW if answered_count(answers) == TOTAL else 0
index = st.session_state["q_index"]


def move(to: int) -> None:
    st.session_state["q_index"] = to


def currency_label(code: str) -> str:
    symbol = CURRENCIES.get(code, "").strip()
    return f"{code} ({symbol})" if symbol and symbol != code else code


def set_country() -> None:
    country = st.session_state["q_country"]
    answers["country"] = country
    if country:
        answers["currency"] = find_country(country)["currency"]  # default; can be changed in Q2
        st.session_state["q_currency"] = answers["currency"]


# ---------------------------------------------------------------- header

CSS = """
<style>
.block-container{max-width:820px}
.q-kicker{display:flex;justify-content:space-between;align-items:center;font-size:13px;
  color:#64748B;margin:0 0 6px}
.q-kicker b{color:#0F172A;font-size:15px}
.q-file{background:#ECFEFF;border:1px solid #A5F3FC;color:#0E7490;border-radius:999px;
  padding:3px 12px;font-weight:600}
.stProgress > div > div > div > div{background:linear-gradient(90deg,#0891B2,#4338CA)}
hr{margin:.6rem 0 1rem !important}
.stProgress{margin-bottom:10px}
.st-key-qcard{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:22px;
  padding:26px 30px 22px;box-shadow:0 14px 40px rgba(15,23,42,.08);position:relative;
  overflow:hidden}
.st-key-qcard::before{content:"";position:absolute;left:0;right:0;top:0;height:6px;
  background:linear-gradient(90deg,#0891B2,#4338CA)}
.q-part{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:#0891B2}
.q-part em{font-style:normal;color:#B91C1C;background:#FEE2E2;border-radius:999px;
  padding:2px 8px;margin-left:8px;letter-spacing:0;text-transform:none}
.q-title{font-size:28px !important;font-weight:800;color:#0F172A;line-height:1.2;
  letter-spacing:-.01em;margin:6px 0 10px}
.q-why{background:#F1F5F9;border-left:4px solid #0891B2;border-radius:10px;padding:10px 14px;
  font-size:14px;line-height:1.5;color:#334155;margin-bottom:6px}
.q-why b{color:#0E7490}
.st-key-qcard [role="radiogroup"]{display:grid;grid-template-columns:1fr 1fr;gap:8px;
  width:100%}
.st-key-qcard [role="radiogroup"] label{border:1.5px solid #E2E8F0;border-radius:12px;
  padding:10px 14px;width:100%;background:#FFFFFF;margin:0}
.st-key-qcard [role="radiogroup"] label:hover{border-color:#67E8F9;background:#F0FDFF}
.st-key-qcard [role="radiogroup"] label:has(input:checked){border-color:#0891B2;
  background:#ECFEFF;box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.st-key-qcard .stRadio > div{width:100%}
.q-rq{font-size:14px;color:#334155}
.q-ra{font-size:14px;font-weight:700;color:#0F172A}
.st-key-qcard .stButton button[kind="tertiary"]{color:#0891B2;font-weight:600;min-height:0;
  padding:0}
.st-key-qcard [data-testid="stHorizontalBlock"]{gap:.5rem}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

top_bar("questions")
file_name = st.session_state.get("file_name") or "Your file"
st.markdown(f'<div class="q-kicker"><b>About your site</b>'
            f'<span class="q-file">{file_name} ✓</span></div>', unsafe_allow_html=True)
progress_slot = st.empty()  # filled at the end, after this run's answer is saved


def show_progress() -> None:
    done = answered_count(answers)
    progress_slot.progress(done / TOTAL, text=f"**{done} of {TOTAL} answered**")


card = st.container(key="qcard")

# ---------------------------------------------------------------- review screen

with card:
    if index == REVIEW:
        st.markdown('<div class="q-part">Last step</div>'
                    '<div class="q-title">Check your answers</div>', unsafe_allow_html=True)
        for i, q in enumerate(QUESTIONS):
            left, middle, right = st.columns([6, 4, 1], vertical_alignment="center")
            left.markdown(f'<div class="q-rq">{i + 1}. {q["title"]}</div>',
                          unsafe_allow_html=True)
            middle.markdown(f'<div class="q-ra">{answer_text(i, answers)}</div>',
                            unsafe_allow_html=True)
            right.button("Edit", key=f"edit_{i}", on_click=move, args=(i,), type="tertiary")
        missing = [i + 1 for i in range(TOTAL) if not is_answered(i, answers)]
        if missing:
            status_box("check", f"Please answer question {', '.join(map(str, missing))} first.")
        _, go, _ = st.columns([1, 2, 1])
        go.button("Analyse my data →", key="analyse", type="primary", disabled=bool(missing),
                  on_click=go_to, args=("analysing",), use_container_width=True)
        show_progress()
        st.stop()

# ---------------------------------------------------------------- one question

with card:
    q = QUESTIONS[index]
    key = q["key"]
    required = "<em>required</em>" if q.get("required") else ""
    st.markdown(f'<div class="q-part">Question {index + 1} of {TOTAL} · {q["part"]}{required}</div>'
                f'<div class="q-title">{q["title"]}</div>'
                f'<div class="q-why"><b>Why we ask:</b> {q["why"]}</div>', unsafe_allow_html=True)

    if key == "location":
        names = country_names()
        current = answers.get("country")
        st.selectbox("Country", names, index=names.index(current) if current in names else None,
                     placeholder="Choose your country…", key="q_country", on_change=set_country)
        answers["city"] = st.text_input("City", value=answers.get("city", ""),
                                        placeholder="e.g. Pune")
        st.caption("Only the city's name is used, to look up its past weather. Your data is never "
                   "sent anywhere.")
        if answers.get("country"):
            status_box("good", f"✓ All costs and savings will be shown in "
                               f"{currency_label(answers['currency'])}, the currency of "
                               f"{answers['country']}.")

    elif key == "price":
        codes = sorted({row["currency"] for row in load_countries().values()})
        if "q_currency" not in st.session_state:
            st.session_state["q_currency"] = answers.get("currency") or "USD"
        left, right = st.columns([2, 1])
        price = left.number_input("Price per kWh (from your bill)", min_value=0.0, step=0.01,
                                  value=float(answers.get("price") or 0.0), format="%.4f")
        currency = right.selectbox("Currency", codes, key="q_currency", format_func=currency_label,
                                   help="Set from your country. Change it only if your bill uses "
                                        "another currency.")
        answers["price"], answers["currency"] = price or None, currency
        st.caption("Use the total price per kWh on your bill (energy charge plus any per-kWh fees). "
                   "Your own bill is more accurate than any national average.")

    elif key == "supply_temp_c":
        unknown = st.checkbox(IDK, value=key in answers and answers[key] is None, key="q_temp_idk")
        if unknown:
            answers[key] = None
            st.caption("We will assume 1 °C of room to raise the temperature (a cautious guess).")
        else:
            temp = st.number_input("Supply air temperature to the servers (°C)", min_value=10.0,
                                   max_value=35.0, step=0.5,
                                   value=float(answers.get(key) or 22.0))
            answers[key] = temp

    else:
        codes = [*OPTIONS[key], "idk"]
        labels = {**OPTIONS[key], "idk": IDK}
        current = ("idk" if answers[key] is None else answers[key]) if key in answers else None
        picked = st.radio(q["title"], codes, format_func=labels.get, label_visibility="collapsed",
                          index=codes.index(current) if current in codes else None, key=f"q_{key}")
        if picked is not None:
            answers[key] = None if picked == "idk" else picked

    back, _, forward = st.columns([1, 2, 1])
    back.button("← Back", key="back", disabled=index == 0, on_click=move, args=(index - 1,),
                use_container_width=True)
    forward.button("Review answers →" if index == TOTAL - 1 else "Next →", key="next",
                   type="primary", disabled=q.get("required", False) and not is_answered(index, answers),
                   on_click=move, args=(index + 1,), use_container_width=True)

show_progress()
