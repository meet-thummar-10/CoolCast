import pytest

from src.savings import net_energy


def test_issue_example():
    out = net_energy(100, 1.5, 0.10, 800, 8, 0.7)
    assert out["saved_kwh"] == pytest.approx(43_800)
    assert out["net_kwh"] == pytest.approx(43_000)
    assert out["new_pue"] == pytest.approx(1.45)
    assert out["cost"] == pytest.approx(344_000)
    assert out["co2_kg"] == pytest.approx(30_100)


def test_no_reduction_means_only_the_ai_cost():
    out = net_energy(100, 1.5, 0.0, 800, 8, 0.7)
    assert out["saved_kwh"] == 0
    assert out["net_kwh"] == -800
    assert out["new_pue"] == 1.5


def test_ai_can_cost_more_than_it_saves():
    # PUE 1.034 like the NLR facility: little overhead left to save.
    out = net_energy(1000, 1.034, 0.01, 5000, 8, 0.7)
    assert out["saved_kwh"] == pytest.approx(2978.4)
    assert out["net_kwh"] < 0
    assert out["cost"] < 0


def test_perfect_pue_has_nothing_to_save():
    assert net_energy(100, 1.0, 0.5, 0, 8, 0.7)["saved_kwh"] == 0


@pytest.mark.parametrize("args, word", [
    ((100, 0.9, 0.1, 0, 8, 0.7), "PUE"),
    ((100, 1.5, 1.2, 0, 8, 0.7), "reduction"),
    ((100, 1.5, -0.1, 0, 8, 0.7), "reduction"),
    ((-1, 1.5, 0.1, 0, 8, 0.7), "it_kw"),
    ((100, 1.5, 0.1, -5, 8, 0.7), "ai_kwh"),
    ((100, 1.5, 0.1, 0, -8, 0.7), "tariff"),
    ((100, 1.5, 0.1, 0, 8, -0.7), "ef"),
])
def test_invalid_inputs(args, word):
    with pytest.raises(ValueError, match=word):
        net_energy(*args)
