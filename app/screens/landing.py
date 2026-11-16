"""Landing page: what CoolCast does, a few facts, and the Upload button."""

import streamlit as st

from app.state import go_to
from app.ui import LOGO_SVG

CSS = """
<style>
.block-container{padding-top:1.2rem;max-width:1280px}
.lp-brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:22px;color:#0F172A}
.lp-brand svg{width:30px;height:30px;stroke:#0891B2}

/* hero */
.st-key-hero{background:radial-gradient(1100px 500px at 85% -10%,#155E75 0%,transparent 60%),
  linear-gradient(135deg,#0F172A 0%,#0B2A3B 55%,#0E7490 130%);border-radius:24px;
  padding:44px 44px 36px;position:relative;overflow:hidden}
.st-key-hero::after{content:"";position:absolute;inset:0;pointer-events:none;opacity:.35;
  background-image:radial-gradient(rgba(255,255,255,.18) 1px,transparent 1px);
  background-size:22px 22px;mask-image:linear-gradient(90deg,transparent 30%,#000 100%)}
.hero-kicker{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:#67E8F9;background:rgba(34,211,238,.12);
  border:1px solid rgba(103,232,249,.35);border-radius:999px;padding:5px 12px}
.hero-title{font-size:52px;line-height:1.05;font-weight:800;color:#FFFFFF;margin:16px 0 14px;
  letter-spacing:-.02em}
.hero-title span{color:#22D3EE}
.hero-sub{font-size:18px;line-height:1.55;color:#CBD5E1;margin:0 0 6px;max-width:560px}
.hero-note{font-size:13px;color:#94A3B8;margin-top:6px}
.st-key-hero .stButton button{background:#22D3EE;color:#0F172A;border:0;font-weight:700;
  padding:.6rem 1.3rem;font-size:16px}
.st-key-hero .stButton button:hover{background:#67E8F9;color:#0F172A}

.glass{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.16);
  border-radius:18px;padding:20px;backdrop-filter:blur(6px);position:relative;z-index:1}
.glass-top{display:flex;justify-content:space-between;align-items:center;font-size:12px;
  letter-spacing:.06em;text-transform:uppercase;color:#94A3B8;font-weight:700}
.glass-top i{font-style:normal;color:#86EFAC;background:rgba(34,197,94,.14);
  border-radius:999px;padding:3px 9px;letter-spacing:0;text-transform:none}
.glass-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}
.tile{background:rgba(15,23,42,.45);border:1px solid rgba(255,255,255,.10);border-radius:12px;
  padding:12px 14px}
.tile small{display:block;font-size:12px;color:#94A3B8}
.tile b{display:block;font-size:26px;color:#FFFFFF;font-weight:700;line-height:1.25;
  font-variant-numeric:tabular-nums}
.tile em{font-style:normal;font-size:12px;color:#67E8F9}
.split{margin-top:14px}
.split small{font-size:12px;color:#94A3B8}
.split-bar{display:flex;height:12px;border-radius:999px;overflow:hidden;margin:6px 0}
.split-legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#CBD5E1}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}

/* fact strip */
.facts{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;
  margin:6px 0 4px}
.fact{border-radius:16px;padding:18px;color:#0F172A;border:1px solid #E2E8F0;background:#FFFFFF;
  position:relative;overflow:hidden}
.fact::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--c)}
.fact b{display:block;font-size:34px;font-weight:800;line-height:1.1;color:var(--c);
  font-variant-numeric:tabular-nums}
.fact span{display:block;font-size:14px;line-height:1.45;color:#334155;margin-top:6px}
.fact small{display:block;font-size:11px;color:#64748B;margin-top:8px}

.sec-title{font-size:28px;font-weight:800;color:#0F172A;margin:26px 0 4px;letter-spacing:-.01em}
.sec-sub{font-size:15px;color:#475569;margin:0 0 14px}

/* how it works */
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.step{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;padding:20px;
  position:relative}
.step-n{width:38px;height:38px;border-radius:12px;display:flex;align-items:center;
  justify-content:center;font-weight:800;color:#FFFFFF;
  background:linear-gradient(135deg,#0891B2,#4338CA);margin-bottom:12px}
.step b{display:block;font-size:17px;color:#0F172A;margin-bottom:6px}
.step span{font-size:14px;line-height:1.5;color:#475569}

/* where the power goes */
.power{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:22px;
  background:#FFFFFF;border:1px solid #E2E8F0;border-radius:20px;padding:24px;
  align-items:center}
.power h4{margin:0 0 8px;font-size:20px;color:#0F172A}
.power p{margin:0 0 10px;font-size:15px;line-height:1.55;color:#475569}
.pbar{display:flex;height:34px;border-radius:10px;overflow:hidden;font-size:12px;font-weight:700;
  color:#FFFFFF}
.pbar div{display:flex;align-items:center;justify-content:center;white-space:nowrap}
.prow{display:flex;justify-content:space-between;font-size:13px;color:#475569;margin:10px 0 4px}

/* features */
.feats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.feat{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:16px;padding:18px;display:flex;
  gap:14px;align-items:flex-start}
.feat-i{flex:0 0 42px;height:42px;border-radius:12px;display:flex;align-items:center;
  justify-content:center;background:var(--bg);color:var(--fg)}
.feat-i svg{width:22px;height:22px}
.feat b{display:block;font-size:16px;color:#0F172A}
.feat span{font-size:14px;line-height:1.45;color:#475569}

/* trust + cta */
.trust{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.trust div{background:#ECFEFF;border:1px solid #A5F3FC;border-radius:14px;padding:16px;
  font-size:14px;line-height:1.5;color:#155E75}
.trust b{display:block;color:#0F172A;font-size:15px;margin-bottom:4px}
.st-key-cta{background:linear-gradient(120deg,#0E7490,#4338CA);border-radius:20px;
  padding:30px 34px;margin-top:22px}
.cta-t{font-size:26px;font-weight:800;color:#FFFFFF;margin:0}
.cta-s{font-size:15px;color:#E0E7FF;margin:4px 0 0}
.st-key-cta .stButton button{background:#FFFFFF;color:#0F172A;border:0;font-weight:700}
.st-key-cta .stButton button:hover{background:#ECFEFF;color:#0F172A}
.fact b{font-size:30px}
@media (max-width:1100px){.facts{grid-template-columns:repeat(2,1fr)}
  .feats{grid-template-columns:repeat(2,1fr)}.hero-title{font-size:40px}}
@media (max-width:640px){.facts,.feats{grid-template-columns:1fr}.st-key-hero{padding:26px 20px}}
/* big upload buttons between sections, and one that stays in view while scrolling */
.st-key-mid1,.st-key-mid2{background:linear-gradient(120deg,#ECFEFF,#EEF2FF);
  border:1px solid #C7D2FE;border-radius:20px;padding:26px 24px 22px;margin:22px 0 6px;
  text-align:center}
.mid-t{font-size:22px;font-weight:800;color:#0F172A;margin:0 0 4px;text-align:center}
.mid-s{font-size:14px;color:#475569;margin:0 0 6px;text-align:center}
.st-key-mid1 .stButton button,.st-key-mid2 .stButton button{
  background:linear-gradient(120deg,#0891B2,#4338CA);color:#FFFFFF;border:0;font-weight:800;
  font-size:20px;padding:1rem 1.5rem;border-radius:14px;
  box-shadow:0 10px 24px rgba(67,56,202,.28)}
.st-key-mid1 .stButton button:hover,.st-key-mid2 .stButton button:hover{
  filter:brightness(1.08);color:#FFFFFF}
.st-key-mid1 .stButton button p,.st-key-mid2 .stButton button p{font-size:20px;font-weight:800}
.st-key-floatcta{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:999;
  width:auto}
.st-key-floatcta .stButton button{background:#0F172A;color:#FFFFFF;border:2px solid #22D3EE;
  border-radius:999px;font-weight:700;padding:.7rem 1.6rem;
  box-shadow:0 12px 30px rgba(15,23,42,.35)}
.st-key-floatcta .stButton button:hover{background:#155E75;color:#FFFFFF;border-color:#67E8F9}
.foot{text-align:center;font-size:12px;color:#64748B;margin:22px 0 6px}
</style>
"""


def big_upload(key: str, title: str, sub: str) -> None:
    """A wide, centred Upload button between two sections."""
    with st.container(key=key):
        st.markdown(f'<p class="mid-t">{title}</p><p class="mid-s">{sub}</p>',
                    unsafe_allow_html=True)
        _, middle, _ = st.columns([1, 2, 1])
        middle.button("Upload your data →", key=f"upload_{key}", on_click=go_to,
                      args=("upload",), use_container_width=True)


def icon(path: str) -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{path}</svg>')


st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------- top bar

left, right = st.columns([5, 1], vertical_alignment="center")
left.markdown(f'<div class="lp-brand">{LOGO_SVG}CoolCast</div>', unsafe_allow_html=True)
right.button("Upload your data", key="upload_top", type="primary", on_click=go_to,
             args=("upload",), use_container_width=True)

# ---------------------------------------------------------------- hero

with st.container(key="hero"):
    text, card = st.columns([6, 5], gap="large", vertical_alignment="center")
    with text:
        st.markdown(
            '<span class="hero-kicker">Free data-centre energy analysis</span>'
            '<div class="hero-title">Find where your data centre '
            "<span>wastes energy</span></div>"
            '<p class="hero-sub">Upload your power data, answer 10 short questions, and see '
            "where energy and money go, how you compare with published global figures, and "
            "which changes could lower your bill, each with a careful, sourced range.</p>",
            unsafe_allow_html=True)
        st.button("Upload your data →", key="upload_hero", on_click=go_to, args=("upload",))
        st.markdown('<div class="hero-note">Works for any country · results in your currency · '
                    "your file is deleted when you exit</div>", unsafe_allow_html=True)
    with card:
        st.markdown(
            '<div class="glass">'
            '<div class="glass-top">Example result<i>● analysis ready</i></div>'
            '<div class="glass-grid">'
            '<div class="tile"><small>PUE</small><b>1.034</b><em>global average 1.52</em></div>'
            '<div class="tile"><small>Top step to cut cost</small><b>55 – 110</b>'
            "<em>MWh a year</em></div>"
            '<div class="tile"><small>Free-cooling hours</small><b>6,460</b>'
            "<em>of 8,760 a year</em></div>"
            '<div class="tile"><small>Periods flagged</small><b>4</b>'
            "<em>worth investigating</em></div>"
            "</div>"
            '<div class="split"><small>Where the overhead comes from</small>'
            '<div class="split-bar"><div style="width:83%;background:#22D3EE"></div>'
            '<div style="width:2%;background:#A5B4FC"></div>'
            '<div style="width:15%;background:#6366F1"></div></div>'
            '<div class="split-legend">'
            '<span><i class="dot" style="background:#22D3EE"></i>Always on 83%</span>'
            '<span><i class="dot" style="background:#A5B4FC"></i>Follows servers 2%</span>'
            '<span><i class="dot" style="background:#6366F1"></i>Follows weather 15%</span>'
            "</div></div></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- facts

FACTS = [
    ("1.52", "Global average PUE: for every 1 kWh the servers use, about 0.5 kWh more goes to "
             "cooling, power losses and lighting.", "Uptime Institute, 2026", "#0891B2"),
    ("2–4%", "Less cooling energy for every 1 °C you raise the supply temperature, inside the "
             "recommended 18–27 °C range.", "Cell Reports Physical Science; ASHRAE", "#4338CA"),
    ("27%", "Less energy when a pump or fan runs just 10 % slower. Speed matters more than "
            "almost anything else.", "Affinity law (ASHE)", "#0E7490"),
    ("15–30%", "Of servers can sit idle, doing no useful work, in sites that never check for "
               "them.", "Uptime Institute", "#7C3AED"),
    ("3,000 h", "A year of cool weather is enough for free cooling with outside air or water "
                "to make sense.", "ENERGY STAR / US DOE", "#059669"),
]
st.markdown('<div class="sec-title">Did you know?</div>'
            '<p class="sec-sub">Five numbers that explain where most data centres can save.</p>'
            '<div class="facts">' + "".join(
                f'<div class="fact" style="--c:{color}"><b>{big}</b><span>{text}</span>'
                f"<small>{source}</small></div>" for big, text, source, color in FACTS)
            + "</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- where the power goes

st.markdown(
    '<div class="sec-title">Where does the power go?</div>'
    '<p class="sec-sub">Every data centre pays for two things: the servers, and everything '
    "needed to keep them running.</p>"
    '<div class="power"><div>'
    "<h4>PUE in one picture</h4>"
    "<p>PUE = total power ÷ IT power. A perfect site would be 1.0: every unit of power reaches "
    "the servers. The gap above 1.0 is <b>overhead</b>, and that is where CoolCast looks for "
    "savings.</p>"
    "<p>CoolCast also splits your overhead into what is <b>always on</b>, what <b>follows the "
    "servers</b> and what <b>follows the weather</b>, so you know which part can be cut.</p>"
    "</div><div>"
    '<div class="prow"><span>Average site · PUE 1.52</span><span>34 % overhead</span></div>'
    '<div class="pbar"><div style="width:66%;background:#0F172A">IT 66%</div>'
    '<div style="width:34%;background:#F59E0B">Overhead 34%</div></div>'
    '<div class="prow"><span>Efficient site · PUE 1.20</span><span>17 % overhead</span></div>'
    '<div class="pbar"><div style="width:83%;background:#0F172A">IT 83%</div>'
    '<div style="width:17%;background:#0891B2">17%</div></div>'
    '<div class="prow"><span>Best in class · PUE 1.09</span><span>8 % overhead</span></div>'
    '<div class="pbar"><div style="width:92%;background:#0F172A">IT 92%</div>'
    '<div style="width:8%;background:#059669"></div></div>'
    "</div></div>", unsafe_allow_html=True)

big_upload("mid1", "See these numbers for your own site",
           "Upload a CSV or Excel file with your power readings. It takes a few minutes.")

# ---------------------------------------------------------------- how it works

STEPS = [
    ("Upload your data", "A CSV or Excel file with hourly IT and total power. Use our template, "
                         "or upload your file as it is and confirm the columns."),
    ("Answer 10 questions", "Your location and electricity price, then a few optional questions "
                            "about your cooling, UPS and plans. \"I don't know\" is always fine."),
    ("Get your analysis", "We clean the data, add past local weather and your grid's CO₂, and "
                          "show where to save, with ranges and sources."),
]
st.markdown('<div class="sec-title">How it works</div>'
            '<p class="sec-sub">Three steps, a few minutes.</p><div class="steps">' + "".join(
                f'<div class="step"><div class="step-n">{n}</div><b>{title}</b>'
                f"<span>{text}</span></div>" for n, (title, text) in enumerate(STEPS, 1))
            + "</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- what you get

FEATURES = [
    ("Energy & Cost", "PUE, overhead, cost and CO₂ in your own currency.",
     '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>', "#CFFAFE", "#0E7490"),
    ("Efficiency & Load", "How efficient you are at every IT load and in every month.",
     '<path d="M4.5 18.5a9 9 0 1 1 15 0"/><path d="M12 14l4.5-5"/>', "#E0E7FF", "#4338CA"),
    ("Cooling & Weather", "How weather drives your cooling, and your free-cooling hours.",
     '<path d="M12 2v20M4.9 6.5l14.2 11M4.9 17.5l14.2-11"/>', "#DBEAFE", "#1D4ED8"),
    ("Anomalies", "Periods that used more energy than the forecast expected.",
     '<path d="M12 3 2 21h20z"/><path d="M12 10v5M12 18h.01"/>', "#FEF3C7", "#B45309"),
    ("How to reduce your cost", "Steps that fit your site, with sourced saving ranges.",
     '<path d="M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>', "#DCFCE7",
     "#15803D"),
    ("Benchmark & Export", "Compare with global figures; download PDF and Excel.",
     '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>', "#F3E8FF", "#7E22CE"),
]
st.markdown('<div class="sec-title">What you get</div>'
            '<p class="sec-sub">Eleven analysis pages, all from your own data.</p>'
            '<div class="feats">' + "".join(
                f'<div class="feat"><div class="feat-i" style="--bg:{bg};--fg:{fg}">{icon(path)}'
                f"</div><div><b>{title}</b><span>{text}</span></div></div>"
                for title, text, path, bg, fg in FEATURES)
            + "</div>", unsafe_allow_html=True)

big_upload("mid2", "Get all eleven pages from your own data",
           "Free, for any country, with results in your currency.")

# ---------------------------------------------------------------- privacy and accuracy

st.markdown(
    '<div class="sec-title">Privacy &amp; accuracy</div>'
    '<p class="sec-sub">Built to be careful with your data and honest about its numbers.</p>'
    '<div class="trust">'
    "<div><b>Your data stays yours</b>Your file is processed in memory for your session only "
    "and deleted when you exit.</div>"
    "<div><b>Only your city is looked up</b>Just the city name is used, to fetch public weather "
    "and grid data.</div>"
    "<div><b>Every number is labelled</b>Measured, modelled or assumed, so you know what to "
    "trust.</div>"
    "<div><b>Ranges, not promises</b>Savings are estimates shown as ranges, and never added "
    "together.</div>"
    "</div>", unsafe_allow_html=True)

with st.container(key="cta"):
    words, action = st.columns([4, 1], vertical_alignment="center")
    words.markdown('<p class="cta-t">Ready to see where your energy goes?</p>'
                   '<p class="cta-s">Start with our template or your own file. It takes a few '
                   "minutes.</p>", unsafe_allow_html=True)
    action.button("Upload your data →", key="upload_bottom", on_click=go_to, args=("upload",),
                  use_container_width=True)

with st.container(key="floatcta"):  # stays at the bottom of the window while scrolling
    st.button("Upload your data →", key="upload_float", on_click=go_to, args=("upload",))

st.markdown('<div class="foot" style="padding-bottom:70px">CoolCast · open-source data-centre energy analysis · figures on '
            "this page are published industry values or an example result</div>",
            unsafe_allow_html=True)
