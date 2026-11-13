"""The 10 questions about the user's site, in order.

Answers are stored in ``st.session_state["answers"]`` with these keys:
country, city, price, currency, site_type, cooling_system, free_cooling,
supply_temp_c, vfd, ups_mode, unused_servers, can_change.
"I don't know" is stored as None. Option codes come from src.recommend.OPTIONS.
"""

from src.recommend import OPTIONS

IDK = "I don't know"

QUESTIONS = [
    {"key": "location", "part": "Your site", "title": "Where is your data centre?",
     "required": True,
     "why": "Your location gives us past local weather for forecasts, your grid's CO₂ per kWh, "
            "your currency and how many hours outside air could cool for free."},
    {"key": "price", "part": "Your site", "title": "What do you pay for electricity?",
     "required": True,
     "why": "Every cost and saving is calculated with this price. Prices vary a lot by "
            "contract, so the figure from your own bill is the most accurate."},
    {"key": "site_type", "part": "Your site", "title": "What type of data centre is it?",
     "why": "We hide steps you cannot act on (for example, a colocation provider cannot switch "
            "off customers' servers)."},
    {"key": "cooling_system", "part": "Cooling", "title": "What is your main cooling system?",
     "why": "Advice depends on the equipment: for example, sites with cooling towers can use "
            "cool water for free cooling."},
    {"key": "free_cooling", "part": "Cooling", "title": "Do you already use free cooling?",
     "why": "If yes, we remove this step. If no, we show how many hours your climate allows."},
    {"key": "supply_temp_c", "part": "Cooling",
     "title": "What temperature do you supply to the servers?",
     "why": "This sets your biggest calculated saving: how many degrees you can still raise "
            "safely (up to the recommended 27 °C)."},
    {"key": "vfd", "part": "Cooling", "title": "Do your pumps and fans have variable-speed drives?",
     "why": "Drives let pumps and fans slow down when full speed is not needed. If all of yours "
            "have them, we remove this step."},
    {"key": "ups_mode", "part": "Power & IT", "title": "How do your UPS units run?",
     "why": "An efficiency mode can cut losses, but it reduces protection. If you already use it, "
            "we remove this step."},
    {"key": "unused_servers", "part": "Power & IT",
     "title": "Do you regularly find and remove unused servers?",
     "why": "Studies estimate 15-30 % of equipment can sit idle without regular checks. This can "
            "be the largest saving."},
    {"key": "can_change", "part": "Your plans", "title": "What kind of changes can you make?",
     "why": "We show the steps that fit: free setting changes, small investments, or larger "
            "projects."},
]
TOTAL = len(QUESTIONS)
CHOICE_KEYS = [q["key"] for q in QUESTIONS if q["key"] in OPTIONS]


def is_answered(index: int, answers: dict) -> bool:
    """Whether question ``index`` has an answer ("I don't know" counts as an answer)."""
    key = QUESTIONS[index]["key"]
    if key == "location":
        return bool(answers.get("country")) and bool(str(answers.get("city") or "").strip())
    if key == "price":
        return (answers.get("price") or 0) > 0 and bool(answers.get("currency"))
    return key in answers


def answered_count(answers: dict) -> int:
    return sum(is_answered(i, answers) for i in range(TOTAL))


def answer_text(index: int, answers: dict) -> str:
    """The answer to question ``index`` in words, for the review screen."""
    key = QUESTIONS[index]["key"]
    if not is_answered(index, answers):
        return "Not answered"
    if key == "location":
        return f"{answers['city'].strip()}, {answers['country']}"
    if key == "price":
        return f"{answers['price']:g} {answers['currency']} per kWh"
    value = answers[key]
    if value is None:
        return IDK
    if key == "supply_temp_c":
        return f"{value:g} °C"
    return OPTIONS[key][value]
