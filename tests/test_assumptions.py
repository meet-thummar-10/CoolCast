import pytest

from src.assumptions import REQUIRED_KEYS, load_assumptions

FRACTIONS = ("greenest_tolerance", "cooling_reduction")


def test_expected_items_present():
    data = load_assumptions()
    assert {"tariff", "emission_factor", *FRACTIONS} <= set(data)


def test_every_item_is_complete_and_labelled():
    for name, item in load_assumptions().items():
        for key in REQUIRED_KEYS:
            assert key in item, f"{name} missing {key}"
        assert item["label"] == "assumed"
        assert item["source"].strip()


def test_values_are_valid():
    data = load_assumptions()
    for name, item in data.items():
        assert item["value"] > 0, name
    for name in FRACTIONS:
        assert 0 < data[name]["value"] < 1, name


def test_missing_key_raises(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[tariff]\nvalue = 8.0\nunit = "₹/kWh"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="tariff"):
        load_assumptions(bad)
