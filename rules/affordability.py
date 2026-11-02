"""
Affordability: can this customer comfortably repay this loan?

Pure Python. No AI. Every figure used in the decision is returned in
`figures`, so the AI can explain it, the trace can record it, and a
reviewer can check it by hand.

Simplification (documented): calculations use floats, and every amount
shown or compared is rounded to whole pence, halves up. A production
system would hold money as integer pence end-to-end.
"""
import math
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from rules import config

AFFORDABLE = "AFFORDABLE"
NOT_AFFORDABLE = "NOT_AFFORDABLE"


def money(amount: float) -> float:
    """Round to whole pence, halves always up (not Python's banker's rounding)."""
    return float(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------- 1. Verify income ----------

@dataclass
class IncomeResult:
    verified_monthly_income: float
    method: str        # "AVERAGE" or "LOWEST_MONTH"
    variation: float   # (highest month - lowest month) / average


def verify_monthly_income(monthly_incomes: list[float]) -> IncomeResult:
    if not monthly_incomes:
        raise ValueError("Need at least one month of income to verify")
    average = sum(monthly_incomes) / len(monthly_incomes)
    if average <= 0:
        return IncomeResult(0.0, "AVERAGE", 0.0)
    variation = (max(monthly_incomes) - min(monthly_incomes)) / average
    if variation > config.INCOME_VARIATION_THRESHOLD:
        # Irregular income: be prudent and use the quietest month.
        return IncomeResult(money(min(monthly_incomes)), "LOWEST_MONTH", round(variation, 4))
    return IncomeResult(money(average), "AVERAGE", round(variation, 4))


# ---------- 2. Repayment maths ----------

def monthly_rate(apr_percent: float) -> float:
    """APR already includes compounding, so the monthly rate is the 12th root, not APR / 12."""
    return (1 + apr_percent / 100) ** (1 / 12) - 1


def monthly_repayment(principal: float, apr_percent: float, term_months: int) -> float:
    """The fixed monthly payment that clears the loan exactly on the last payment."""
    r = monthly_rate(apr_percent)
    if r == 0:
        return money(principal / term_months)
    return money(principal * r / (1 - (1 + r) ** -term_months))


def max_principal_for_repayment(repayment: float, apr_percent: float, term_months: int) -> float:
    """The reverse calculation: the most you can borrow for a given monthly payment."""
    r = monthly_rate(apr_percent)
    if r == 0:
        return repayment * term_months
    return repayment * (1 - (1 + r) ** -term_months) / r


# ---------- 3. The affordability decision ----------

@dataclass
class AffordabilityResult:
    outcome: str
    reasons: list[str] = field(default_factory=list)
    figures: dict = field(default_factory=dict)


def check_affordability(
    *,
    verified_monthly_income: float,
    committed_outgoings: float,
    dependants: int,
    loan_amount: float,
    term_months: int,
    apr_percent: float,
) -> AffordabilityResult:
    living_allowance = (config.LIVING_COST_BASE_GBP
                        + config.LIVING_COST_PER_DEPENDANT_GBP * dependants)
    disposable = money(verified_monthly_income - committed_outgoings - living_allowance)

    stress_apr = round(apr_percent + config.STRESS_TEST_UPLIFT_PERCENTAGE_POINTS, 2)
    repayment = monthly_repayment(loan_amount, apr_percent, term_months)
    stress_repayment = monthly_repayment(loan_amount, stress_apr, term_months)
    max_allowed = money(max(disposable, 0) * config.MAX_REPAYMENT_SHARE_OF_DISPOSABLE)

    # Largest loan that passes the stress test, rounded DOWN to the nearest £100.
    if max_allowed > 0:
        exact_max = max_principal_for_repayment(max_allowed, stress_apr, term_months)
        max_amount = math.floor(exact_max / 100) * 100
    else:
        max_amount = 0

    figures = {
        "verified_monthly_income": money(verified_monthly_income),
        "committed_outgoings": money(committed_outgoings),
        "living_cost_allowance": money(living_allowance),
        "disposable_income": disposable,
        "apr_percent": apr_percent,
        "monthly_repayment": repayment,
        "stress_apr_percent": stress_apr,
        "stress_monthly_repayment": stress_repayment,
        "max_allowed_repayment": max_allowed,
        "max_affordable_amount": max_amount,
    }

    if disposable <= 0:
        return AffordabilityResult(NOT_AFFORDABLE, ["NO_DISPOSABLE_INCOME"], figures)
    if stress_repayment > max_allowed:
        return AffordabilityResult(NOT_AFFORDABLE, ["REPAYMENT_EXCEEDS_LIMIT"], figures)
    return AffordabilityResult(AFFORDABLE, [], figures)
