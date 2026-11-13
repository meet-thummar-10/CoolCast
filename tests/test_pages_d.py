import io

import pytest
from conftest import open_page
from openpyxl import load_workbook

PAGES = {"9_Benchmark.py": "Benchmark", "10_Export.py": "Export", "11_Replay.py": "Replay"}


@pytest.mark.parametrize("page, title", PAGES.items())
def test_pages_load_with_development_data(page, title, demo_analysis):
    at = open_page(page, demo_analysis)
    assert not at.exception, page
    assert at.title[0].value == title


@pytest.mark.parametrize("page", PAGES)
def test_pages_load_with_only_it_and_total_power(page, minimal_analysis):
    assert not open_page(page, minimal_analysis).exception


@pytest.mark.parametrize("page", PAGES)
def test_pages_without_analysis_ask_for_upload(page):
    assert open_page(page).button(key="no_results_upload")


def metrics(at):
    return {m.label: m.value for m in at.metric}


def test_benchmark_numbers_and_warning(demo_analysis):
    at = open_page("9_Benchmark.py", demo_analysis)
    m = metrics(at)
    assert m["Your PUE"] == "1.034"
    assert m["Global average"] == "1.52"
    assert m["Energy avoided vs average"].startswith("≈ 8.")  # ≈ 8.3 GWh
    assert any("unusually low" in w.value for w in at.warning)


def test_every_download_has_a_file(demo_analysis):
    at = open_page("10_Export.py", demo_analysis)
    buttons = at.get("download_button")
    assert len(buttons) == 8  # PDF, Excel and 6 CSV tables
    names = [b.proto.label for b in buttons]
    assert names[:2] == ["Download PDF report", "Download Excel (.xlsx)"]


def test_export_files_are_valid(demo_analysis):
    from src.export import build_excel, build_pdf

    _, results, _ = demo_analysis
    assert build_pdf(results).startswith(b"%PDF")
    assert "label" in [c.value for c in load_workbook(io.BytesIO(build_excel(results)))
                       ["Summary"][1]]


def test_replay_starts_on_the_peak_week_and_moves(demo_analysis):
    at = open_page("11_Replay.py", demo_analysis)
    assert metrics(at)["Energy so far"]
    at.slider(key="replay_pos").set_value(10).run()
    first = metrics(at)["Now showing"]
    at.slider(key="replay_pos").set_value(20).run()
    assert metrics(at)["Now showing"] != first
