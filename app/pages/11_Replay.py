"""11 Replay: play a week back hour by hour, actual against forecast."""

import pandas as pd
import streamlit as st

from app.components import empty_state, kpi_card, line_chart
from app.formatting import fmt_energy
from app.page_utils import page_start

results = page_start("Replay", "Play a week back hour by hour and watch actual power against the "
                               "forecast.")
fc = results.get("forecast")
if fc is None:
    empty_state("Replay needs a forecast, and there was not enough data to train one.")
    st.stop()

preds = fc["predictions"]
weeks = preds["ts"].dt.to_period("W").drop_duplicates().tolist()
labels = [f"{w.start_time:%d %b %Y} – {w.end_time:%d %b %Y}" for w in weeks]
peak = preds.groupby(preds["ts"].dt.to_period("W"))["actual"].max().idxmax()
week = st.selectbox("Week", range(len(weeks)), index=weeks.index(peak),
                    format_func=labels.__getitem__, key="replay_week")
data = preds[preds["ts"].dt.to_period("W") == weeks[week]].reset_index(drop=True)
data = pd.DataFrame({"ts": data["ts"], "actual": data["actual"], "forecast": data[fc["best"]]})
last = len(data) - 1

state = st.session_state
if state.get("replay_for") != week:
    state.update(replay_for=week, replay_pos=0, replay_playing=False)

play, speed_col = st.columns([1, 3], vertical_alignment="bottom")
play.button("⏸ Pause" if state["replay_playing"] else "▶ Play", key="replay_play",
            on_click=lambda: state.update(replay_playing=not state["replay_playing"]))
speed = speed_col.select_slider("Speed (hours per step)", [1, 2, 4, 8], value=2,
                                key="replay_speed")


@st.fragment(run_every=0.5)
def player() -> None:
    if state["replay_playing"]:
        state["replay_pos"] = min(state["replay_pos"] + speed, last)
        if state["replay_pos"] >= last:
            state["replay_playing"] = False
    pos = st.slider("Hour", 0, last, key="replay_pos", label_visibility="collapsed")
    shown = data.iloc[: pos + 1]
    now = shown.iloc[-1]
    a, b = st.columns(2)
    c, d = st.columns(2)
    with a:
        kpi_card("Now showing", f"{now['ts']:%a %d %b, %H:%M}", "measured")
    with b:
        kpi_card("Power, actual", f"{now['actual']:.1f} kW", "measured")
    with c:
        kpi_card("Power, forecast", f"{now['forecast']:.1f} kW", "modelled")
    with d:
        kpi_card("Energy so far", fmt_energy(shown["actual"].sum()), "measured")
    line_chart(shown, "ts", ["actual", "forecast"], title=f"Week of {labels[week]}",
               y_label="kW")


player()
