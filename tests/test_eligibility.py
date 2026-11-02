"""
Tests for rules/eligibility.py.

Pattern: start from an applicant who passes everything, then change
ONE thing per test. If a test fails, you know exactly which rule broke.
Boundary values (exactly 18, exactly £1,000, exactly 36 months) are
tested on purpose, because that is where real defects hide.
"""
import pytest

from rules.eligibility import check_eligibility, ELIGIBLE, DECLINED, REFER


def applicant(**changes):
    """A customer who passes every check. Tests override one field at a time."""
    base = dict(
        age=35,
        uk_resident=True,
        credit_band="B",
        months_since_last_default=None,
        months_of_history=3,
        verified_monthly_income=2500,
    )
    base.update(changes)
    return base


def test_happy_path_is_eligible():
    result = check_eligibility(**applicant())
    assert result.outcome == ELIGIBLE
    assert result.reasons == []


def test_under_18_is_declined():
    result = check_eligibility(**applicant(age=17))
    assert result.outcome == DECLINED
    assert result.reasons == ["UNDER_MIN_AGE"]


def test_exactly_18_is_eligible():
    assert check_eligibility(**applicant(age=18)).outcome == ELIGIBLE


def test_non_uk_resident_is_declined():
    result = check_eligibility(**applicant(uk_resident=False))
    assert result.reasons == ["NOT_UK_RESIDENT"]


def test_default_35_months_ago_is_declined():
    result = check_eligibility(**applicant(months_since_last_default=35))
    assert result.reasons == ["RECENT_DEFAULT"]


def test_default_exactly_36_months_ago_is_eligible():
    result = check_eligibility(**applicant(months_since_last_default=36))
    assert result.outcome == ELIGIBLE


def test_band_e_is_declined():
    result = check_eligibility(**applicant(credit_band="E"))
    assert result.reasons == ["CREDIT_BAND_NOT_OFFERED"]


def test_band_d_is_eligible():
    assert check_eligibility(**applicant(credit_band="D")).outcome == ELIGIBLE


def test_two_months_history_is_referred_to_a_person():
    result = check_eligibility(**applicant(months_of_history=2))
    assert result.outcome == REFER
    assert result.reasons == ["INSUFFICIENT_HISTORY"]


def test_income_just_below_minimum_is_declined():
    result = check_eligibility(**applicant(verified_monthly_income=999.99))
    assert result.reasons == ["INCOME_BELOW_MINIMUM"]


def test_income_exactly_minimum_is_eligible():
    result = check_eligibility(**applicant(verified_monthly_income=1000))
    assert result.outcome == ELIGIBLE


def test_all_failed_reasons_are_reported():
    result = check_eligibility(**applicant(age=17, credit_band="E"))
    assert result.outcome == DECLINED
    assert result.reasons == ["UNDER_MIN_AGE", "CREDIT_BAND_NOT_OFFERED"]


def test_hard_decline_beats_referral():
    result = check_eligibility(**applicant(age=17, months_of_history=1))
    assert result.outcome == DECLINED


def test_unknown_credit_band_raises_error():
    with pytest.raises(ValueError):
        check_eligibility(**applicant(credit_band="Z"))
