"""Evaluate simple rule-based baselines on the labelled data (plausible salaries, D-003).

Run from the project root:
    python scripts/baseline_rules.py
"""
from pathlib import Path

import duckdb

from exec_screener.baseline import EXEC_TITLE_PATTERN, SENIOR_TITLE_PATTERN
from exec_screener.salary import BENCHMARK, SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

# The target: full-time-equivalent annual salary >= $100k, plausible salaries only.
LABELLED = f"""
SELECT *, annual_salary >= {BENCHMARK} AS label
FROM ({SALARY_SQL})
WHERE salary_quality = 'ok'
"""

RULES = {
    'always "below benchmark"': "FALSE",
    "experience = Director/Executive": "formatted_experience_level IN ('Director', 'Executive')",
    "title: executive keywords": f"regexp_matches(title, '{EXEC_TITLE_PATTERN}')",
    "title: executive + senior keywords": f"regexp_matches(title, '{SENIOR_TITLE_PATTERN}')",
}


def predicted(rule_sql: str) -> str:
    """A rule as a SQL condition that is never NULL (missing title/level counts as 'no')."""
    return f"COALESCE({rule_sql}, FALSE)"


def confusion(rule_sql: str):
    """Return (TP, FP, FN, TN) for a rule."""
    pred = predicted(rule_sql)
    return con.sql(f"""
        SELECT
            COUNT(*) FILTER (WHERE {pred} AND label),
            COUNT(*) FILTER (WHERE {pred} AND NOT label),
            COUNT(*) FILTER (WHERE NOT {pred} AND label),
            COUNT(*) FILTER (WHERE NOT {pred} AND NOT label)
        FROM ({LABELLED})
    """).fetchall()[0]


n, n_pos = con.sql(f"SELECT COUNT(*), COUNT(*) FILTER (WHERE label) FROM ({LABELLED})").fetchall()[0]
print(f"Labelled postings: {n:,}   at or above benchmark: {n_pos:,} ({n_pos / n:.1%})\n")

print(f"1. Baselines")
print(f"   {'rule':36s} {'flagged':>8s} {'accuracy':>9s} {'precision':>10s} {'recall':>7s} {'F1':>6s}")
for name, rule_sql in RULES.items():
    tp, fp, fn, tn = confusion(rule_sql)
    accuracy = (tp + tn) / n
    precision = tp / (tp + fp) if tp + fp > 0 else None
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall) if tp > 0 else 0.0
    precision_text = "-" if precision is None else f"{precision:.1%}"
    print(f"   {name:36s} {tp + fp:>8,} {accuracy:>9.1%} {precision_text:>10s} {recall:>7.1%} {f1:>6.3f}")


def top_titles(where: str, limit: int):
    """Most frequent (lower-cased) titles among labelled postings matching a condition."""
    return con.sql(f"""
        SELECT lower(title), COUNT(*)
        FROM ({LABELLED})
        WHERE {where}
        GROUP BY lower(title)
        ORDER BY COUNT(*) DESC, lower(title)
        LIMIT {limit}
    """).fetchall()


exec_rule = predicted(RULES["title: executive keywords"])
print("\n2. Executive-keyword rule: most frequent MISSED titles (>= $100k, not flagged)")
for title, count in top_titles(f"label AND NOT {exec_rule}", 8):
    print(f"   {count:>4}  {title}")
print("\n3. Executive-keyword rule: most frequent FALSE ALARMS (flagged, < $100k)")
for title, count in top_titles(f"NOT label AND {exec_rule}", 6):
    print(f"   {count:>4}  {title}")