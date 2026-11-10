"""Annualise disclosed salaries and check them for plausibility.

Reads the database built by scripts/build_db.py.
Run from the project root:
    python scripts/annualise_salary.py
"""
from pathlib import Path

import duckdb

DB_PATH = Path("data/processed/linkedin.duckdb")

FLOOR = 7.25 * 2080  # US federal minimum wage, full-time, full-year = $15,080
CEILING = 1_000_000  # generous upper bound for a single base salary
BENCHMARK = 100_000  # executive salary benchmark

con = duckdb.connect(str(DB_PATH), read_only=True)

# One annual salary per posting that discloses any salary information.
ANNUALISED = """
WITH disclosed AS (
    SELECT
        job_id,
        pay_period,
        normalized_salary,
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
)
SELECT
    *,
    point_salary * CASE pay_period
        WHEN 'YEARLY'   THEN 1
        WHEN 'MONTHLY'  THEN 12
        WHEN 'BIWEEKLY' THEN 26
        WHEN 'WEEKLY'   THEN 52
        WHEN 'HOURLY'   THEN 2080
    END AS annual_salary
FROM disclosed
"""

# --- 1. How was each point estimate obtained? ------------------------------
print("1. Point estimate method")
method_counts = con.sql(f"""
    SELECT point_method, COUNT(*) FROM ({ANNUALISED})
    GROUP BY point_method ORDER BY COUNT(*) DESC
""").fetchall()
for method, n in method_counts:
    print(f"   {method:15s} {n:>7,}")

# --- 2. Does our formula reproduce the dataset's normalized_salary? --------
n_total, n_unmapped, n_missing_norm, n_mismatch = con.sql(f"""
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE annual_salary IS NULL),
        COUNT(*) FILTER (WHERE normalized_salary IS NULL),
        COUNT(*) FILTER (WHERE abs(annual_salary - normalized_salary) > 0.01)
    FROM ({ANNUALISED})
""").fetchall()[0]
print("\n2. Our annual salary vs. the dataset's normalized_salary")
print(f"   postings with salary:            {n_total:>7,}")
print(f"   unknown pay period (no factor):  {n_unmapped:>7,}")
print(f"   normalized_salary missing:       {n_missing_norm:>7,}")
print(f"   differ by more than $0.01:       {n_mismatch:>7,}")

# --- 3. Plausibility per pay period -----------------------------------------
rows = con.sql(f"""
    SELECT
        pay_period,
        COUNT(*),
        median(annual_salary),
        COUNT(*) FILTER (WHERE annual_salary < {FLOOR}),
        COUNT(*) FILTER (WHERE annual_salary > {CEILING}),
        avg(CASE WHEN annual_salary >= {BENCHMARK} THEN 1 ELSE 0 END)
    FROM ({ANNUALISED})
    GROUP BY pay_period
    ORDER BY COUNT(*) DESC
""").fetchall()
print(f"\n3. Plausibility (band ${FLOOR:,.0f} to ${CEILING:,.0f})")
print(f"   {'pay_period':10s} {'n':>7s} {'median':>11s} {'<floor':>7s} {'>ceiling':>9s} {'>=100k':>7s}")
for period, n, median, below, above, share in rows:
    print(f"   {period:10s} {n:>7,} {median:>11,.0f} {below:>7,} {above:>9,} {share:>7.1%}")