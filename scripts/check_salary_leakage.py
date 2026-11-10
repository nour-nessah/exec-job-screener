"""Measure how often job descriptions mention salary amounts as text (target leakage).

Run from the project root:
    python scripts/check_salary_leakage.py
"""
from pathlib import Path

import duckdb

from exec_screener.salary import SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

PATTERNS = {
    "dollar amount ($ + digit)": r"\$\s?\d",
    "yearly-style amount": r"\$\s?\d{2,3},\d{3}|\$\s?\d{2,3}(\.\d+)?\s?[kK]\b",
    "hourly-style amount": r"(?i)\$\s?\d{1,3}(\.\d{2})?\s*(/|per)\s*(hour|hr)\b",
}

BASE = f"""
SELECT p.job_id, p.title, p.description, s.job_id IS NOT NULL AS disclosed
FROM postings p
LEFT JOIN (SELECT job_id FROM ({SALARY_SQL})) s ON s.job_id = p.job_id
"""

conditions = {label: f"regexp_matches(description, '{pattern}')" for label, pattern in PATTERNS.items()}
conditions["any salary amount"] = (
    f"({conditions['yearly-style amount']} OR {conditions['hourly-style amount']})"
)

n_disc, n_non = con.sql(
    f"SELECT COUNT(*) FILTER (WHERE disclosed), COUNT(*) FILTER (WHERE NOT disclosed) FROM ({BASE})"
).fetchall()[0]

print("1. Share of descriptions mentioning an amount")
print(f"   {'pattern':28s} {'disclosers':>11s} {'non-discl.':>11s}   (counts)")
for label, condition in conditions.items():
    k_disc, k_non = con.sql(f"""
        SELECT
            COUNT(*) FILTER (WHERE disclosed AND {condition}),
            COUNT(*) FILTER (WHERE NOT disclosed AND {condition})
        FROM ({BASE})
    """).fetchall()[0]
    print(f"   {label:28s} {k_disc / n_disc:>11.1%} {k_non / n_non:>11.1%}   ({k_disc:,} / {k_non:,})")

print("\n2. Non-disclosers with a yearly-style amount in the text (first 6)")
yearly = PATTERNS["yearly-style amount"]
examples = con.sql(f"""
    SELECT job_id, title, regexp_extract(description, '{yearly}')
    FROM ({BASE})
    WHERE NOT disclosed AND regexp_matches(description, '{yearly}')
    ORDER BY job_id
    LIMIT 6
""").fetchall()
for job_id, title, amount in examples:
    print(f"   {job_id:>10}  {str(title)[:45]:45s} {amount}")