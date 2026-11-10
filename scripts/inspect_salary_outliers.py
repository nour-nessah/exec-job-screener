"""Inspect implausible salaries: compare raw values with their claimed pay period.

Uses the shared salary rules in src/exec_screener/salary.py.
Run from the project root:
    python scripts/inspect_salary_outliers.py
"""
from pathlib import Path

import duckdb

from exec_screener.salary import SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

BUCKETS = [
    ("0", "point_salary = 0"),
    ("(0,100)", "point_salary > 0 AND point_salary < 100"),
    ("[100,1k)", "point_salary >= 100 AND point_salary < 1000"),
    ("[1k,10k)", "point_salary >= 1000 AND point_salary < 10000"),
    ("[10k,100k)", "point_salary >= 10000 AND point_salary < 100000"),
    (">=100k", "point_salary >= 100000"),
]


def fmt(value) -> str:
    """Format a salary value; missing values (None) are shown as '-'."""
    return "-" if value is None else f"{value:,.0f}"


def show_examples(heading: str, where: str, order: str = "job_id", limit: int = 10) -> None:
    """Print example postings that match a SQL condition."""
    print(f"\n{heading}")
    examples = con.sql(f"""
        SELECT job_id, title, min_salary, med_salary, max_salary
        FROM ({SALARY_SQL})
        WHERE {where}
        ORDER BY {order}
        LIMIT {limit}
    """).fetchall()
    print(f"   {'job_id':>10s}  {'title':45s} {'min':>9s} {'median':>9s} {'max':>9s}")
    for job_id, job_title, lo, med, hi in examples:
        print(f"   {job_id:>10}  {job_title[:45]:45s} {fmt(lo):>9s} {fmt(med):>9s} {fmt(hi):>9s}")


# --- 1. Raw values per pay period -------------------------------------------
bucket_counts = ", ".join(f"COUNT(*) FILTER (WHERE {condition})" for _, condition in BUCKETS)
rows = con.sql(f"""
    SELECT pay_period, {bucket_counts}
    FROM ({SALARY_SQL})
    GROUP BY pay_period
    ORDER BY COUNT(*) DESC
""").fetchall()

print("1. Raw salary values per pay period (before annualisation)")
print(f"   {'pay_period':10s}" + "".join(f"{label:>11s}" for label, _ in BUCKETS))
for period, *counts in rows:
    print(f"   {period:10s}" + "".join(f"{count:>11,}" for count in counts))

# --- 2-4. Look at the suspicious rows themselves ----------------------------
show_examples("2. All BIWEEKLY postings", "pay_period = 'BIWEEKLY'")
show_examples(
    "3. HOURLY postings with a raw value >= 1,000 per hour (top 5)",
    "pay_period = 'HOURLY' AND point_salary >= 1000",
    order="point_salary DESC, job_id",
    limit=5,
)
show_examples(
    "4. YEARLY postings with a raw value between 0 and 1,000 (first 8)",
    "pay_period = 'YEARLY' AND point_salary > 0 AND point_salary < 1000",
    limit=8,
)