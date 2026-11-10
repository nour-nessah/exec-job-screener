"""Salary rules shared by all analyses: point estimate, annualisation, plausibility.

The reasoning behind each rule is documented in docs/decisions.md (D-001 to D-004).
"""

FLOOR = 7.25 * 2080  # D-002: US federal minimum wage, full-time, full-year = $15,080
CEILING = 1_000_000  # D-002: generous upper bound for a single base salary
BENCHMARK = 100_000  # executive salary benchmark

# D-002: multiply a salary stated per pay period by this factor to get a yearly amount.
# D-004: the result is FULL-TIME-EQUIVALENT pay of the role (40 h x 52 weeks for hourly),
#        not what one person earns in a calendar year.
ANNUAL_FACTORS = {
    "YEARLY": 1,
    "MONTHLY": 12,
    "BIWEEKLY": 26,
    "WEEKLY": 52,
    "HOURLY": 2080,
}

_FACTOR_CASES = "\n".join(
    f"            WHEN '{period}' THEN {factor}" for period, factor in ANNUAL_FACTORS.items()
)

# One row per posting that discloses a salary, with every postings column plus:
#   point_salary, point_method, annual_salary (full-time-equivalent, D-004), salary_quality
SALARY_SQL = f"""
WITH disclosed AS (
    SELECT
        *,
        CASE
            WHEN min_salary IS NOT NULL AND max_salary IS NOT NULL
                THEN (min_salary + max_salary) / 2
            ELSE med_salary
        END AS point_salary,
        CASE
            WHEN min_salary IS NOT NULL AND max_salary IS NOT NULL THEN 'range midpoint'
            ELSE 'median only'
        END AS point_method
    FROM postings
    WHERE min_salary IS NOT NULL OR med_salary IS NOT NULL OR max_salary IS NOT NULL
),
annualised AS (
    SELECT
        *,
        point_salary * CASE pay_period
{_FACTOR_CASES}
        END AS annual_salary
    FROM disclosed
)
SELECT
    *,
    CASE
        WHEN annual_salary IS NULL THEN 'unknown_period'
        WHEN annual_salary < {FLOOR} THEN 'below_floor'
        WHEN annual_salary > {CEILING} THEN 'above_ceiling'
        ELSE 'ok'
    END AS salary_quality
FROM annualised
"""