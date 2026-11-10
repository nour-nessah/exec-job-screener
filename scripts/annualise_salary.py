"""Annualise disclosed salaries and check them for plausibility.

Uses the shared salary rules in src/exec_screener/salary.py.
Run from the project root:
    python scripts/annualise_salary.py
"""
from pathlib import Path

import duckdb

from exec_screener.salary import BENCHMARK, CEILING, FLOOR, SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

# --- 1. How was each point estimate obtained? ------------------------------
print("1. Point estimate method")
method_counts = con.sql(f"""
    SELECT point_method, COUNT(*) FROM ({SALARY_SQL})
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
    FROM ({SALARY_SQL})
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
    FROM ({SALARY_SQL})
    GROUP BY pay_period
    ORDER BY COUNT(*) DESC
""").fetchall()
print(f"\n3. Plausibility (band ${FLOOR:,.0f} to ${CEILING:,.0f})")
print(f"   {'pay_period':10s} {'n':>7s} {'median':>11s} {'<floor':>7s} {'>ceiling':>9s} {'>=100k':>7s}")
for period, n, median, below, above, share in rows:
    print(f"   {period:10s} {n:>7,} {median:>11,.0f} {below:>7,} {above:>9,} {share:>7.1%}")