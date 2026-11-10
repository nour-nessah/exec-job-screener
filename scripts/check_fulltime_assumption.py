"""Check the 'full-time, all year' assumption behind HOURLY x 2080.

Uses only plausible salaries (salary_quality = 'ok', decision D-003).
Run from the project root:
    python scripts/check_fulltime_assumption.py
"""
from pathlib import Path

import duckdb

from exec_screener.salary import BENCHMARK, SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

OK_SALARIES = f"SELECT * FROM ({SALARY_SQL}) WHERE salary_quality = 'ok'"

# --- 1. Hourly vs yearly pay, by work type ----------------------------------
rows = con.sql(f"""
    SELECT
        pay_period,
        work_type,
        COUNT(*),
        median(point_salary),
        median(annual_salary),
        avg(CASE WHEN annual_salary >= {BENCHMARK} THEN 1 ELSE 0 END)
    FROM ({OK_SALARIES})
    WHERE pay_period IN ('HOURLY', 'YEARLY')
    GROUP BY pay_period, work_type
    ORDER BY pay_period, COUNT(*) DESC
""").fetchall()

print("1. Plausible salaries by pay period and work type")
print(f"   {'pay_period':10s} {'work_type':11s} {'n':>7s} {'median raw':>11s} {'median annual':>14s} {'>=100k':>7s}")
for period, work_type, n, median_raw, median_annual, share in rows:
    raw = f"{median_raw:,.2f}" if period == "HOURLY" else f"{median_raw:,.0f}"
    print(f"   {period:10s} {work_type:11s} {n:>7,} {raw:>11s} {median_annual:>14,.0f} {share:>7.1%}")

# --- 2. Sensitivity: what if hourly contracts are not paid all year? -------
n_ok = con.sql(f"SELECT COUNT(*) FROM ({OK_SALARIES})").fetchall()[0][0]
print("\n2. Sensitivity: hourly CONTRACT jobs paid for only part of the year")
print(f"   {'share of year':>13s} {'jobs >= 100k':>13s} {'share':>7s} {'change':>8s}")
baseline = None
for fraction in [1.0, 0.75, 0.5]:
    n_benchmark = con.sql(f"""
        SELECT COUNT(*) FILTER (
            WHERE annual_salary
                * CASE WHEN pay_period = 'HOURLY' AND work_type = 'CONTRACT' THEN {fraction} ELSE 1 END
                >= {BENCHMARK}
        )
        FROM ({OK_SALARIES})
    """).fetchall()[0][0]
    baseline = baseline if baseline is not None else n_benchmark
    print(f"   {fraction:>13.0%} {n_benchmark:>13,} {n_benchmark / n_ok:>7.1%} {n_benchmark - baseline:>+8,}")