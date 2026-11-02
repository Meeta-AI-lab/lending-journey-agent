"""
Rule thresholds for the lending simulation: the single source of truth.

These are SYNTHETIC assumptions for a portfolio project. They are not the
criteria of Barclays or any other real bank.

If you change a value here, update the matching policy document in
data/policies/ so the agent never tells customers something different
from what the rules actually do.
"""

# --- Eligibility (see data/policies/eligibility.md) ---
MIN_AGE = 18
MIN_MONTHLY_INCOME_GBP = 1000
DEFAULT_LOOKBACK_MONTHS = 36
VALID_CREDIT_BANDS = {"A", "B", "C", "D", "E"}
DECLINED_CREDIT_BANDS = {"E"}
MIN_HISTORY_MONTHS = 3

# --- Affordability (see data/policies/affordability.md) ---
LIVING_COST_BASE_GBP = 600
LIVING_COST_PER_DEPENDANT_GBP = 250
STRESS_TEST_UPLIFT_PERCENTAGE_POINTS = 3.0
MAX_REPAYMENT_SHARE_OF_DISPOSABLE = 0.40
INCOME_VARIATION_THRESHOLD = 0.30
