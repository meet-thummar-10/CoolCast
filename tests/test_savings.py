import pytest

from src.savings import LIKELY, NONE, UNCERTAIN, savings_range

# Development data: yearly IT energy and PUE.
IT, PUE = 17_048_000, 1.034


def run(cut=(5, 15), off=(0, 0), tariff=8, ef=0.675, cost=0, it=IT, pue=PUE):
    return savings_range(it, pue, *cut, *off, tariff, ef, cost)


def test_issue_example():
    out = run()
    assert out["kwh"] == pytest.approx((28_981.6, 86_944.8))
    assert out["money"] == pytest.approx((231_852.8, 695_558.4))
    assert out["co2_kg"] == pytest.approx((19_562.6, 58_687.7), abs=0.1)
    assert out["new_pue"] == pytest.approx((1.0289, 1.0323))
    assert out["verdict"] == LIKELY
    assert out["payback_years"] is None


def test_low_and_high_in_either_order():
    assert run(cut=(15, 5)) == run(cut=(5, 15))


def test_verdicts():
    assert run(cut=(0, 10))["verdict"] == UNCERTAIN
    assert run(cut=(0, 0))["verdict"] == NONE
    assert run(cut=(0, 0), off=(1, 2))["verdict"] == LIKELY


def test_payback():
    out = run(cost=1_000_000)
    assert out["payback_years"] == pytest.approx((1.44, 4.31), abs=0.01)
    assert run(cut=(0, 10), cost=1_000_000)["payback_years"][1] is None
    assert run(cut=(0, 0), cost=1_000_000)["payback_years"] is None


def test_switching_off_it_also_removes_its_overhead():
    # 1 % of IT off, no overhead cut: saves 1 % of the total, not just 1 % of IT.
    out = run(cut=(0, 0), off=(1, 1))
    assert out["kwh"][0] == pytest.approx(IT * PUE * 0.01)


def test_changes_are_combined_not_added():
    both = run(cut=(10, 10), off=(10, 10))["kwh"][0]
    separate = run(cut=(10, 10))["kwh"][0] + run(cut=(0, 0), off=(10, 10))["kwh"][0]
    assert both < separate


def test_perfect_pue_has_no_overhead_to_cut():
    out = run(pue=1.0)
    assert out["kwh"] == (0, 0)
    assert out["verdict"] == NONE


@pytest.mark.parametrize("kwargs, word", [
    ({"pue": 0.9}, "PUE"),
    ({"cut": (5, 120)}, "cut_high"),
    ({"cut": (-1, 5)}, "cut_low"),
    ({"off": (0, 101)}, "it_off_high"),
    ({"it": -1}, "it_kwh"),
    ({"tariff": -8}, "tariff"),
    ({"ef": -0.7}, "ef"),
    ({"cost": -5}, "one_off_cost"),
])
def test_invalid_inputs(kwargs, word):
    with pytest.raises(ValueError, match=word):
        run(**kwargs)
