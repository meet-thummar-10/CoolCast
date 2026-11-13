import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.components import (
    HIGHLIGHT,
    bar_chart,
    heatmap,
    kpi_card,
    line_chart,
    scatter,
    status_box,
    tag_html,
)

DF = pd.DataFrame({
    "ts": pd.date_range("2023-01-01", periods=4, freq="h"),
    "it_kw": [100.0, 110, 130, 120],
    "cooling_kw": [5.0, 6, 7, 8],
    "temp_c": [1.0, 2, 3, 4],
})


def test_invalid_tag_or_status_raises():
    with pytest.raises(ValueError, match="measured"):
        kpi_card("PUE", "1.03", tag="guessed")
    with pytest.raises(ValueError, match="good"):
        status_box("great", "text")


def test_measured_is_solid_and_estimate_is_dashed():
    assert "solid" in tag_html("measured") and "dashed" not in tag_html("measured")
    for tag in ("modelled", "assumed", "estimate"):
        assert "dashed" in tag_html(tag)


def test_line_chart_uses_readable_names():
    fig = line_chart(DF, "ts", ["it_kw", "cooling_kw"], title="Power", show=False)
    assert [t.name for t in fig.data] == ["IT (kW)", "Cooling (kW)"]


def test_unit_dropped_from_legend_when_axis_has_it():
    fig = bar_chart(DF, "ts", ["it_kw", "cooling_kw"], y_label="kWh", show=False)
    assert [t.name for t in fig.data] == ["IT", "Cooling"]


def test_highest_bar_is_highlighted():
    fig = bar_chart(DF, "ts", "it_kw", highlight_max=True, show=False)
    colors = list(fig.data[0].marker.color)
    assert colors[2] == HIGHLIGHT and colors.count(HIGHLIGHT) == 1


def test_other_charts_build():
    assert len(scatter(DF, "temp_c", "cooling_kw", color="it_kw", show=False).data) == 1
    table = pd.DataFrame([[1, 2], [3, 4]], index=["Jan", "Feb"], columns=[0, 1])
    assert len(heatmap(table, show=False).data) == 1


def demo_page():
    import pandas as pd

    from app.components import (
        empty_state,
        error_state,
        kpi_card,
        line_chart,
        status_box,
    )

    kpi_card("PUE", "1.034", tag="measured")
    kpi_card("Saving", "₹4.4 – 8.8 lakh", tag="estimate")
    kpi_card("Tariff", "₹8/kWh", tag="assumed")
    df = pd.DataFrame({"ts": pd.date_range("2023-01-01", periods=3, freq="h"), "it_kw": [1, 2, 3]})
    line_chart(df, "ts", "it_kw")
    status_box("good", "Better than the global average.")
    status_box("check", "Limited data.")
    empty_state("No data in this range.")
    error_state("Could not load the data.")


def test_components_render_in_streamlit():
    at = AppTest.from_function(demo_page, default_timeout=30)
    at.run()
    assert not at.exception
    assert [m.value for m in at.metric] == ["1.034", "₹4.4 – 8.8 lakh", "₹8/kWh"]
    assert at.success[0].value == "Better than the global average."
    assert at.warning[0].value == "Limited data."
    assert at.info[0].value == "No data in this range."
    assert at.error[0].value == "Could not load the data."
