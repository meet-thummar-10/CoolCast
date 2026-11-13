from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.upload import example_csv

APP = str(Path(__file__).resolve().parent.parent / "app" / "Home.py")


def screen():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["stage"] = "upload"
    return at.run()


def upload(at, name, content: bytes):
    at.file_uploader(key="file").upload(name, content, "text/csv").run()
    return at


def hours_csv(days, **extra) -> bytes:
    ts = pd.date_range("2024-01-01", periods=days * 24, freq="h")
    df = pd.DataFrame({"timestamp": ts.strftime("%Y-%m-%d %H:%M"), "it_kw": 1000.0,
                       "total_kw": 1100.0, **extra})
    return df.to_csv(index=False).encode()


def continue_button(at):
    return at.button(key="next")


def test_before_upload_shows_both_ways_and_downloads():
    at = screen()
    assert not at.exception
    assert at.title[0].value == "Upload your data"
    subheaders = [s.value for s in at.subheader]
    assert "Use our template" in subheaders and "Upload your file as it is" in subheaders
    assert len(at.get("download_button")) == 2


def test_example_file_passes_and_continue_saves_the_data():
    at = upload(screen(), "coolcast_example.csv", example_csv())
    assert not at.exception
    assert not at.error
    assert any("6 months or more" in s.value for s in at.success)
    button = continue_button(at)
    assert not button.disabled
    button.click().run()
    assert at.session_state["stage"] == "questions"
    assert at.session_state["file_name"] == "coolcast_example.csv"
    assert len(at.session_state["data"]) > 4000
    assert at.session_state["data_level"] == "good"


def test_twelve_days_is_blocked():
    at = upload(screen(), "short.csv", hours_csv(12))
    assert any("at least 1 month" in e.value for e in at.error)
    assert continue_button(at).disabled


def test_three_months_gives_the_limited_data_warning():
    at = upload(screen(), "quarter.csv", hours_csv(90))
    assert any("Limited data" in w.value for w in at.warning)
    assert not continue_button(at).disabled


def test_changing_a_column_changes_the_checks():
    content = hours_csv(40, other_kw=10.0)
    at = upload(screen(), "site.csv", content)
    assert not at.error
    total = at.selectbox(key="map_2")  # the total_kw column
    total.set_value("(not used)").run()
    # still valid: total is added up from IT + the "other" part
    assert not at.error
    at.selectbox(key="map_3").set_value("(not used)").run()
    assert any("Total facility power is required" in e.value for e in at.error)


def test_ambiguous_dates_ask_day_or_month_first():
    ts = pd.date_range("2024-01-01", periods=24 * 40, freq="h")
    df = pd.DataFrame({"timestamp": [t.strftime("%m/%d/%Y %H:%M") for t in ts],
                       "it_kw": 1000.0, "total_kw": 1100.0})
    df = df[ts.day <= 12]  # only days 1-12, so 03/04 could be either order
    at = upload(screen(), "dates.csv", df.to_csv(index=False).encode())
    assert at.radio(key="dayfirst")
    at.radio(key="dayfirst").set_value("Month first (01/31/2024)").run()
    assert not at.exception


def test_unreadable_file_shows_a_clear_error():
    at = upload(screen(), "bad.csv", b"just,some\ntext,here\n")
    assert at.error
    assert continue_button_missing(at)


def continue_button_missing(at):
    return not [b for b in at.button if b.key == "next"]
