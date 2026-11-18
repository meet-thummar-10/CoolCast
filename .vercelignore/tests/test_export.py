import io

import pandas as pd
import pytest
from openpyxl import load_workbook

from src.data import load_demo_data
from src.export import (
    SHEETS,
    build_excel,
    build_pdf,
    collect_results,
    fmt_energy,
    fmt_money,
    fmt_range,
)

ANSWERS = {"country": "India", "city": "Pune", "price": 8, "currency": "INR",
           "site_type": "hpc", "cooling_system": "water_chillers", "free_cooling": "no",
           "supply_temp_c": 22, "vfd": "some", "ups_mode": "double_conversion",
           "unused_servers": "sometimes", "can_change": "small"}
LOCATION = {"emission_factor": 0.675, "ef_source": "CEA v22", "free_cooling_hours": 6460}


@pytest.fixture(scope="module")
def results():
    return collect_results(load_demo_data(), ANSWERS, LOCATION, "my_datacentre_2023.csv")


def pdf_text(data: bytes) -> str:
    """Text of a PDF made by fpdf2 (uncompressed text streams are not used, so decode pages)."""
    import zlib

    chunks = []
    for part in data.split(b"stream")[1:]:
        body = part.split(b"endstream")[0].strip(b"\r\n")
        try:
            chunks.append(zlib.decompress(body).decode("latin-1"))
        except zlib.error:
            chunks.append(body.decode("latin-1", "ignore"))
    return "".join(chunks)


def test_results_have_every_part(results):
    for key in ("kpis", "quality", "monthly", "anomalies", "steps", "forecast", "benchmark",
                "overhead", "answers", "location"):
        assert key in results
    assert results["kpis"]["pue"] == pytest.approx(1.034, abs=0.0005)
    assert len(results["monthly"]) == 12


def test_excel_has_the_seven_sheets_each_with_a_label_column(results):
    book = load_workbook(io.BytesIO(build_excel(results)))
    assert book.sheetnames == SHEETS
    for sheet in book:
        header = [c.value for c in sheet[1]]
        assert "label" in header, sheet.title


def test_excel_numbers_are_numbers(results):
    monthly = pd.read_excel(io.BytesIO(build_excel(results)), sheet_name="Monthly")
    assert pd.api.types.is_numeric_dtype(monthly["total_kwh"])
    summary = pd.read_excel(io.BytesIO(build_excel(results)), sheet_name="Summary")
    assert summary.set_index("metric").loc["PUE", "value"] == pytest.approx(1.034, abs=0.0005)


def test_pdf_is_a_report_with_the_key_results(results):
    data = build_pdf(results)
    assert data.startswith(b"%PDF")
    text = pdf_text(data)
    assert "1.034" in text
    assert "55 - 110 MWh" in text
    assert "Do not add the ranges together" in text


def test_no_file_adds_up_the_steps(results):
    steps = pd.read_excel(io.BytesIO(build_excel(results)), sheet_name="Steps to reduce cost")
    assert len(steps) == len(results["steps"]["steps"])  # one row per step, no sum row
    text = pdf_text(build_pdf(results)).lower()
    assert "total saving" not in text and "all steps together" not in text


def test_works_with_only_it_and_total_power():
    df = load_demo_data()[["ts", "it_kw", "total_kw"]]
    res = collect_results(df, {"price": 0.12, "currency": "USD"}, {})
    assert build_pdf(res).startswith(b"%PDF")
    assert load_workbook(io.BytesIO(build_excel(res))).sheetnames == SHEETS


@pytest.mark.parametrize("low, high, fmt, args, text", [
    (55_140, 110_280, fmt_energy, (), "55 - 110 MWh"),
    (441_104, 882_207, fmt_money, ("INR",), "INR 4.4 - 8.8 lakh"),
    (0, 849_836, fmt_money, ("INR",), "INR 0 - 8.5 lakh"),
    (3_400_000, 5_100_000, fmt_money, ("EUR",), "EUR 3.4 - 5.1 million"),
])
def test_ranges_in_the_report(low, high, fmt, args, text):
    assert fmt_range(low, high, fmt, *args) == text
