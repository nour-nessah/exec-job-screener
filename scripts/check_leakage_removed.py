"""Verify on all real descriptions that strip_salary_amounts removes salary amounts (D-006).

Run from the project root:
    python scripts/check_leakage_removed.py
"""
import re
from pathlib import Path

import duckdb

from exec_screener.salary import SALARY_SQL
from exec_screener.text import LEAKAGE_PATTERNS, strip_salary_amounts

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

rows = con.sql(f"""
    SELECT p.description, s.job_id IS NOT NULL AS disclosed
    FROM postings p
    LEFT JOIN (SELECT job_id FROM ({SALARY_SQL})) s ON s.job_id = p.job_id
""").fetchall()

originals = [description for description, _ in rows]
cleaned = [strip_salary_amounts(description) for description in originals]
disclosed = [is_disclosed for _, is_disclosed in rows]

n_changed = sum(
    1 for before, after in zip(originals, cleaned) if before is not None and before != after
)
print(f"Descriptions changed by the cleaner: {n_changed:,} of {len(rows):,} ({n_changed / len(rows):.1%})")

print("\nMatches in DISCLOSERS' descriptions (the training data)")
print(f"   {'pattern':28s} {'before':>8s} {'after':>8s}")
for label, pattern in LEAKAGE_PATTERNS.items():
    regex = re.compile(pattern)
    before = sum(
        1 for text, d in zip(originals, disclosed) if d and text is not None and regex.search(text)
    )
    after = sum(1 for text, d in zip(cleaned, disclosed) if d and regex.search(text))
    print(f"   {label:28s} {before:>8,} {after:>8,}")