"""Questions screen: 10 questions, one per screen, then a review screen.

Answers go to st.session_state["answers"] (keys in app/questions.py).
Question 1 (location) and 2 (electricity price) are required; the others
accept "I don't know", which leads to a cautious assumption.
"""

import streamlit as st

from app.components import error_state, status_box
from app.formatting import CURRENCIES
from app.questions import (
    IDK,
    QUESTIONS,
    TOTAL,
    answer_text,
    answered_count,
    check_answer,
    is_answered,
)
from app.state import go_to
from app.ui import top_bar
from src.location import (
    LocationError,
    country_names,
    find_country,
    get_location,
    load_countries,
)
from src.recommend import OPTIONS

REVIEW = TOTAL  # index of the review screen
answers: dict = st.session_state.setdefault("answers", {})
if "q_index" not in st.session_state:
    st.session_state["q_index"] = REVIEW if answered_count(answers) == TOTAL else 0
index = st.session_state["q_index"]


def move(to: int) -> None:
    st.session_state["q_index"] = to
    st.session_state["q_error"] = None


def sync(key: str) -> None:
    """Copy what is typed or picked for this question into the answers.

    Called from the page and from the Next button, so Next works straight after
    typing, without pressing Enter first.
    """
    state = st.session_state
    if key == "location":
        if "q_country" in state:
            answers["country"] = state["q_country"]
        if "q_city" in state:
            answers["city"] = state["q_city"]
    elif key == "price":
        if "q_price" in state:
            answers["price"] = state["q_price"]
        if "q_currency" in state:
            answers["currency"] = state["q_currency"]
    elif key == "supply_temp_c":
        if state.get("q_temp_idk"):
            answers[key] = None
        elif "q_temp" in state:
            if state["q_temp"] is None:
                answers.pop(key, None)
            else:
                answers[key] = state["q_temp"]
    elif state.get(f"q_{key}") is not None:
        answers[key] = None if state[f"q_{key}"] == "idk" else state[f"q_{key}"]


def verify_city() -> tuple[str | None, str | None]:
    """Check with the map service that the city exists in the country: (error, note)."""
    place = (answers["country"], answers["city"].strip().lower())
    if st.session_state.get("q_verified") == place:
        return None, None
    try:
        found = get_location(answers["country"], answers["city"])
    except LocationError as err:
        if "could not be reached" in str(err):
            return None, ("We could not check the city right now (no connection to the map "
                          "service). Please make sure it is spelled correctly.")
        return str(err), None
    st.session_state["q_verified"] = place
    answers["city"] = found["city"]
    return None, None


def go_next() -> None:
    """Next button: save the answer, check it, and only then move on."""
    state = st.session_state
    key = QUESTIONS[index]["key"]
    sync(key)
    error, note = check_answer(index, answers)
    if not error and key == "location":
        error, city_note = verify_city()
        note = note or city_note
    state["q_note"], state["q_note_at"] = note, index + 1 if not error else index
    if error:
        state["q_error"], state["q_error_at"] = error, index
        return
    move(index + 1)


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
.q-ok{font-size:13px;color:#166534;background:#F0FDF4;border-radius:10px;padding:8px 12px;
  line-height:1.45}
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
        st.text_input("City", value=answers.get("city", ""), placeholder="e.g. Pune",
                      key="q_city")
        if answers.get("country"):
            st.markdown(f'<div class="q-ok">✓ Results will be shown in '
                        f'<b>{currency_label(answers["currency"])}</b>, the currency of '
                        f'{answers["country"]}. Only the city\'s name is looked up; your data is '
                        "never sent anywhere.</div>", unsafe_allow_html=True)
        else:
            st.caption("Only the city's name is used, to look up its past weather. Your data is "
                       "never sent anywhere.")

    elif key == "price":
        codes = sorted({row["currency"] for row in load_countries().values()})
        if "q_currency" not in st.session_state:
            st.session_state["q_currency"] = answers.get("currency") or "USD"
        left, right = st.columns([2, 1])
        left.number_input("Price per kWh (from your bill)", min_value=0.0, step=0.01,
                          value=answers.get("price"), placeholder="e.g. 8.50", key="q_price")
        right.selectbox("Currency", codes, key="q_currency", format_func=currency_label,
                        help="Set from your country. Change it only if your bill uses another "
                             "currency.")
        st.caption("Use the total price per kWh on your bill (energy charge plus any per-kWh fees). "
                   "Your own bill is more accurate than any national average.")

    elif key == "supply_temp_c":
        unknown = st.checkbox(IDK, value=key in answers and answers[key] is None, key="q_temp_idk")
        if unknown:
            st.caption("We will assume 1 °C of room to raise the temperature (a cautious guess).")
        else:
            st.number_input("Supply air temperature to the servers (°C)", step=0.5,
                            value=answers.get(key), placeholder="e.g. 22", key="q_temp")
            st.caption("Most data centres supply air between 18 and 27 °C.")

    else:
        codes = [*OPTIONS[key], "idk"]
        labels = {**OPTIONS[key], "idk": IDK}
        current = ("idk" if answers[key] is None else answers[key]) if key in answers else None
        st.radio(q["title"], codes, format_func=labels.get, label_visibility="collapsed",
                 index=codes.index(current) if current in codes else None, key=f"q_{key}")

    sync(key)
    if st.session_state.get("q_error_at") == index and st.session_state.get("q_error"):
        error_state(st.session_state["q_error"])
    elif st.session_state.get("q_note_at") == index and st.session_state.get("q_note"):
        status_box("check", st.session_state["q_note"])

    back, _, forward = st.columns([1, 2, 1])
    back.button("← Back", key="back", disabled=index == 0, on_click=move, args=(index - 1,),
                use_container_width=True)
    forward.button("Review answers →" if index == TOTAL - 1 else "Next →", key="next",
                   type="primary", on_click=go_next, use_container_width=True)

show_progress()
