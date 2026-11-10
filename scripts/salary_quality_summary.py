"""Summarise salary quality flags, using the shared salary rules.

Run from the project root:
    python scripts/salary_quality_summary.py
"""
from pathlib import Path

import duckdb

from exec_screener.salary import BENCHMARK, SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

rows = con.sql(f"""
    SELECT
        salary_quality,
        COUNT(*),
        COUNT(*) FILTER (WHERE annual_salary >= {BENCHMARK})
    FROM ({SALARY_SQL})
    GROUP BY salary_quality
    ORDER BY COUNT(*) DESC
""").fetchall()

print(f"{'salary_quality':15s} {'postings':>9s} {'>= $100k':>9s}")
for quality, n, n_benchmark in rows:
    print(f"{quality:15s} {n:>9,} {n_benchmark:>9,}")