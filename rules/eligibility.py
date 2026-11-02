"""
Eligibility check: can this customer be considered for a loan at all?

Pure Python. No AI. The same inputs always give the same answer.
Returns machine-readable reason codes, which the AI later turns into
plain English. The AI never decides the outcome itself.
"""
from dataclasses import dataclass, field

from rules import config

ELIGIBLE = "ELIGIBLE"
DECLINED = "DECLINED"
REFER = "REFER"  # cannot decide automatically, so pass to a person


@dataclass
class EligibilityResult:
    outcome: str
    reasons: list[str] = field(default_factory=list)


def check_eligibility(
    *,
    age: int,
    uk_resident: bool,
    credit_band: str,
    months_since_last_default: int | None,
    months_of_history: int,
    verified_monthly_income: float,
) -> EligibilityResult:
    # 0. Bad input is a bug, not a customer outcome, so fail loudly.
    if credit_band not in config.VALID_CREDIT_BANDS:
        raise ValueError(f"Unknown credit band: {credit_band!r}")

    # 1. Hard criteria. Any failure is a decline. Collect every failure.
    reasons = []
    if age < config.MIN_AGE:
        reasons.append("UNDER_MIN_AGE")
    if not uk_resident:
        reasons.append("NOT_UK_RESIDENT")
    if (months_since_last_default is not None
            and months_since_last_default < config.DEFAULT_LOOKBACK_MONTHS):
        reasons.append("RECENT_DEFAULT")
    if credit_band in config.DECLINED_CREDIT_BANDS:
        reasons.append("CREDIT_BAND_NOT_OFFERED")
    if reasons:
        return EligibilityResult(DECLINED, reasons)

    # 2. Too little bank history to verify income, so a person must review.
    if months_of_history < config.MIN_HISTORY_MONTHS:
        return EligibilityResult(REFER, ["INSUFFICIENT_HISTORY"])

    # 3. Verified income below the minimum.
    if verified_monthly_income < config.MIN_MONTHLY_INCOME_GBP:
        return EligibilityResult(DECLINED, ["INCOME_BELOW_MINIMUM"])

    return EligibilityResult(ELIGIBLE)
