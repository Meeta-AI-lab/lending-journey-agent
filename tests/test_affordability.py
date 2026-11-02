"""
Tests for rules/affordability.py.

Covers income verification (including the 30% boundary), the repayment
maths, rounding, and the affordability decision, including proof that
the 'largest amount we can offer' really is the largest.
"""
import pytest

from rules.affordability import (
    AFFORDABLE, NOT_AFFORDABLE, check_affordability, money,
    monthly_repayment, verify_monthly_income,
)


# ---------- Income verification ----------

def test_steady_income_uses_the_average():
    result = verify_monthly_income([2000, 2100, 2050])
    assert result.method == "AVERAGE"
    assert result.verified_monthly_income == 2050.00


def test_irregular_income_uses_the_lowest_month():
    result = verify_monthly_income([3000, 1500, 2500])
    assert result.method == "LOWEST_MONTH"
    assert result.verified_monthly_income == 1500.00


def test_variation_of_exactly_30_percent_still_uses_the_average():
    # (1150 - 850) / 1000 = 0.30, which is not MORE than 30%
    result = verify_monthly_income([1150, 1000, 850])
    assert result.method == "AVERAGE"
    assert result.verified_monthly_income == 1000.00


def test_no_income_data_raises_an_error():
    with pytest.raises(ValueError):
        verify_monthly_income([])


# ---------- Repayment maths and rounding ----------

def test_zero_interest_repayment_is_simple_division():
    assert monthly_repayment(1200, 0, 12) == 100.00


def test_known_repayment_value():
    # £10,000 over 60 months at 6.9% APR, hand-calculated with the
    # standard amortisation formula: about £196.56 a month.
    assert monthly_repayment(10000, 6.9, 60) == pytest.approx(196.56, abs=0.05)


def test_interest_means_you_repay_more_than_you_borrowed():
    assert monthly_repayment(10000, 6.9, 60) * 60 > 10000


def test_money_rounds_halves_up():
    # Python's own round(2.675, 2) gives 2.67. Our money() must give 2.68.
    assert money(2.675) == 2.68


# ---------- The affordability decision ----------

def application(**changes):
    """An application that passes comfortably. Tests change one thing at a time."""
    base = dict(
        verified_monthly_income=3000,
        committed_outgoings=1200,
        dependants=0,
        loan_amount=10000,
        term_months=60,
        apr_percent=6.9,
    )
    base.update(changes)
    return base


def test_comfortable_loan_is_affordable_with_correct_workings():
    result = check_affordability(**application())
    assert result.outcome == AFFORDABLE
    assert result.figures["living_cost_allowance"] == 600
    assert result.figures["disposable_income"] == 1200      # 3000 - 1200 - 600
    assert result.figures["max_allowed_repayment"] == 480   # 40% of 1200
    assert result.figures["stress_apr_percent"] == 9.9      # 6.9 + 3


def test_stress_repayment_is_higher_than_the_real_repayment():
    figures = check_affordability(**application()).figures
    assert figures["stress_monthly_repayment"] > figures["monthly_repayment"]


def test_dependants_increase_the_living_allowance():
    result = check_affordability(**application(dependants=2))
    assert result.figures["living_cost_allowance"] == 1100  # 600 + 2 x 250
    assert result.figures["disposable_income"] == 700       # 3000 - 1200 - 1100


def test_large_loan_is_declined_with_a_lower_amount_offered():
    result = check_affordability(**application(loan_amount=25000))
    assert result.outcome == NOT_AFFORDABLE
    assert result.reasons == ["REPAYMENT_EXCEEDS_LIMIT"]
    assert 0 < result.figures["max_affordable_amount"] < 25000
    assert result.figures["max_affordable_amount"] % 100 == 0


def test_offered_maximum_really_is_the_maximum():
    offered = check_affordability(**application(loan_amount=25000)).figures["max_affordable_amount"]
    assert check_affordability(**application(loan_amount=offered)).outcome == AFFORDABLE
    assert check_affordability(**application(loan_amount=offered + 100)).outcome == NOT_AFFORDABLE


def test_no_disposable_income_is_not_affordable():
    # 1500 - 1000 - 600 = -100
    result = check_affordability(**application(verified_monthly_income=1500, committed_outgoings=1000))
    assert result.outcome == NOT_AFFORDABLE
    assert result.reasons == ["NO_DISPOSABLE_INCOME"]
    assert result.figures["max_affordable_amount"] == 0
