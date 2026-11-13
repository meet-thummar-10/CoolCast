"""Reusable page building blocks so every page looks the same.

Every number shown to users carries a tag. "Measured" (straight from the
user's file) is a solid label; "modelled", "assumed" and "estimate" are
dashed labels, so the difference is clear by shape, not only by colour.
"""

import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

INK = "#0F172A"
PRIMARY = "#0891B2"
HIGHLIGHT = "#4338CA"
FONT = "Inter, system-ui, sans-serif"

TAGS = {
    "measured": ("Measured", "From your uploaded file"),
    "modelled": ("Modelled", "Calculated by a model from your data"),
    "assumed": ("Assumed", "From your answers or a published source"),
    "estimate": ("Estimate", "A careful range, not a promise"),
}

STATUS = {
    "good": st.success,      # green: saving or good result
    "check": st.warning,     # amber: check this
    "problem": st.error,     # red: problem
}

# One colour per series, used by every chart.
COLORS = {
    "it_kw": PRIMARY,
    "total_kw": INK,
    "overhead_kw": "#0E7490",
    "mechanical_kw": "#155E75",
    "cooling_kw": "#0E7490",
    "pump_kw": "#64748B",
    "hvac_kw": "#94A3B8",
    "plug_kw": "#CBD5E1",
    "other_kw": "#475569",
    "actual": INK,
    "forecast": HIGHLIGHT,
}
SEQUENCE = [PRIMARY, HIGHLIGHT, "#64748B", "#0E7490", "#94A3B8", INK]
SCALE = [[0, "#ECFEFF"], [0.5, "#22D3EE"], [1, "#155E75"]]

LABELS = {
    "ts": "Time",
    "it_kw": "IT (kW)",
    "total_kw": "Total (kW)",
    "overhead_kw": "Overhead (kW)",
    "cooling_kw": "Cooling (kW)",
    "pump_kw": "Pumps (kW)",
    "hvac_kw": "Air handling (kW)",
    "plug_kw": "Lights and plugs (kW)",
    "other_kw": "Other (kW)",
    "mechanical_kw": "Cooling system (kW)",
    "temp_c": "Outdoor temperature (°C)",
    "humidity_pct": "Humidity (%)",
    "pue": "PUE",
    "actual": "Actual",
    "forecast": "Forecast",
}


def _check_tag(tag: str) -> None:
    if tag not in TAGS:
        raise ValueError(f"tag must be one of {', '.join(TAGS)}, got {tag!r}")


def tag_html(tag: str) -> str:
    """HTML for a small label: solid for measured, dashed for everything else."""
    _check_tag(tag)
    text, meaning = TAGS[tag]
    if tag == "measured":
        style = f"background:{INK};color:#FFFFFF;border:1.5px solid {INK}"
    else:
        style = "background:transparent;color:#374151;border:1.5px dashed #6B7280"
    return (f'<span title="{html.escape(meaning)}" style="{style};font-size:11px;'
            f'font-weight:700;padding:2px 8px;border-radius:999px">{text}</span>')


def kpi_card(label: str, value: str, tag: str, help: str | None = None) -> None:
    """A bordered metric with its tag. ``value`` is already formatted (see formatting.py)."""
    _check_tag(tag)
    with st.container(border=True):
        st.metric(label, value, help=help)
        st.markdown(tag_html(tag), unsafe_allow_html=True)


def status_box(kind: str, text: str) -> None:
    """Green "good", amber "check" or red "problem" message."""
    if kind not in STATUS:
        raise ValueError(f"kind must be one of {', '.join(STATUS)}, got {kind!r}")
    STATUS[kind](text)


def _style(fig: go.Figure, title: str | None, y_label: str | None = None) -> go.Figure:
    # Title at the very top, legend in its own row between the title and the plot.
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "y": 0.98, "yanchor": "top"} if title else None,
        font={"family": FONT, "color": INK},
        margin={"l": 10, "r": 10, "t": 90 if title else 40, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0, "title": None},
        hovermode="x unified",
        plot_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(gridcolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#E2E8F0")
    if y_label:
        fig.update_yaxes(title=y_label)
    return fig


def _series_name(column: str, y_label: str | None) -> str:
    """Readable series name; the unit is dropped when the axis already shows it."""
    name = LABELS.get(column, column)
    return name.split(" (")[0] if y_label else name


def _labels(columns) -> dict:
    return {c: LABELS.get(c, c) for c in columns}


def _colors(ys) -> dict:
    return {c: COLORS[c] for c in ys if c in COLORS}


def line_chart(df: pd.DataFrame, x: str, y, title=None, y_label=None, show=True) -> go.Figure:
    """Line chart of one or more columns against ``x``."""
    ys = [y] if isinstance(y, str) else list(y)
    fig = px.line(df, x=x, y=ys, labels=_labels([x, *ys]), color_discrete_map=_colors(ys),
                  color_discrete_sequence=SEQUENCE)
    fig.for_each_trace(lambda t: t.update(name=_series_name(t.name, y_label)))
    _style(fig, title, y_label)
    if show:
        st.plotly_chart(fig)
    return fig


def bar_chart(df: pd.DataFrame, x: str, y, title=None, y_label=None, stacked=True,
              highlight_max=False, show=True) -> go.Figure:
    """Bar chart; several ``y`` columns are stacked unless ``stacked=False``.

    With one ``y`` column and ``highlight_max=True``, the highest bar is drawn
    in the highlight colour so the eye goes straight to it.
    """
    ys = [y] if isinstance(y, str) else list(y)
    fig = px.bar(df, x=x, y=ys, labels=_labels([x, *ys]),
                 barmode="stack" if stacked else "group",
                 color_discrete_map=_colors(ys), color_discrete_sequence=SEQUENCE)
    fig.for_each_trace(lambda t: t.update(name=_series_name(t.name, y_label)))
    if highlight_max and len(ys) == 1 and len(df):
        top = df[ys[0]].idxmax()
        fig.data[0].marker.color = [HIGHLIGHT if i == top else COLORS.get(ys[0], PRIMARY)
                                    for i in df.index]
    _style(fig, title, y_label)
    if show:
        st.plotly_chart(fig)
    return fig


def scatter(df: pd.DataFrame, x: str, y: str, color: str | None = None, title=None,
            show=True) -> go.Figure:
    """Scatter plot, optionally coloured by a numeric column."""
    fig = px.scatter(df, x=x, y=y, color=color, labels=_labels([x, y, color or x]),
                     opacity=0.5, color_continuous_scale=SCALE,
                     color_discrete_sequence=[PRIMARY])
    fig.update_traces(marker={"size": 4})
    _style(fig, title)
    fig.update_layout(hovermode="closest")
    if show:
        st.plotly_chart(fig)
    return fig


def heatmap(table: pd.DataFrame, title=None, x_label=None, y_label=None, z_label=None,
            show=True) -> go.Figure:
    """Heatmap of a pivot table (index on the y axis, columns on the x axis)."""
    fig = px.imshow(table, aspect="auto", color_continuous_scale=SCALE,
                    labels={"x": x_label, "y": y_label, "color": z_label})
    _style(fig, title)
    fig.update_layout(hovermode="closest")
    if show:
        st.plotly_chart(fig)
    return fig


def empty_state(message: str) -> None:
    """Shown when there is nothing to display, e.g. no data in the chosen range."""
    st.info(message, icon="ℹ️")


def error_state(message: str) -> None:
    """Shown when something went wrong, in plain language."""
    st.error(message, icon="⚠️")
