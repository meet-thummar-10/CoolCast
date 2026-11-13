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

top_bar("questions")
st.title("About your site")
st.caption(f"{st.session_state.get('file_name') or 'Your file'} ✓")
progress_slot = st.empty()  # filled at the end, after this run's answer is saved


def show_progress() -> None:
    done = answered_count(answers)
    progress_slot.progress(done / TOTAL, text=f"**{done} of {TOTAL} answered**")


# ---------------------------------------------------------------- review screen

if index == REVIEW:
    st.subheader("Check your answers")
    for i, q in enumerate(QUESTIONS):
        left, middle, right = st.columns([4, 4, 1], vertical_alignment="center")
        left.markdown(f"**{i + 1}. {q['title']}**")
        middle.write(answer_text(i, answers))
        right.button("Edit", key=f"edit_{i}", on_click=move, args=(i,), type="tertiary")
    missing = [i + 1 for i in range(TOTAL) if not is_answered(i, answers)]
    if missing:
        status_box("check", f"Please answer question {', '.join(map(str, missing))} first.")
    st.button("Analyse my data →", key="analyse", type="primary", disabled=bool(missing),
              on_click=go_to, args=("analysing",))
    show_progress()
    st.stop()

# ---------------------------------------------------------------- one question

q = QUESTIONS[index]
key = q["key"]
st.caption(f"Question {index + 1} of {TOTAL} · {q['part']}"
           + (" · required" if q.get("required") else ""))
st.subheader(q["title"])
st.info(f"**Why we ask:** {q['why']}", icon=":material/info:")

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

# ---------------------------------------------------------------- navigation

back, _, forward = st.columns([1, 3, 1])
back.button("← Back", key="back", disabled=index == 0, on_click=move, args=(index - 1,))
forward.button("Review answers →" if index == TOTAL - 1 else "Next →", key="next",
               type="primary", disabled=q.get("required", False) and not is_answered(index, answers),
               on_click=move, args=(index + 1,))
if not q.get("required"):
    st.caption("Not sure? Choose \"I don't know\" — we will use a cautious assumption.")
show_progress()
