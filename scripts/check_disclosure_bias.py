"""Compare postings that disclose a salary with those that don't (salary-disclosure bias).

Uses the shared salary rules: a posting 'discloses' if it appears in SALARY_SQL.
Run from the project root:
    python scripts/check_disclosure_bias.py
"""
from pathlib import Path

import duckdb

from exec_screener.salary import BENCHMARK, SALARY_SQL

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

# US states requiring salary ranges in job postings during the data period (2023-2024):
# Colorado, California, Washington, New York (NYC from Nov 2022, statewide from Sep 2023).
PAY_TRANSPARENCY_STATES = ("CA", "CO", "NY", "WA")
STATE_REGEX = r",\s*([A-Z]{2})$"  # "San Francisco, CA" -> "CA"

BASE = f"""
SELECT
    p.*,
    s.job_id IS NOT NULL AS disclosed,
    COALESCE(p.formatted_experience_level, 'missing') AS experience,
    COALESCE(CAST(CAST(c.company_size AS INTEGER) AS VARCHAR), 'missing') AS company_size_group,
    CASE
        WHEN regexp_extract(p.location, '{STATE_REGEX}', 1) IN {PAY_TRANSPARENCY_STATES}
            THEN 'pay-transparency state'
        WHEN regexp_extract(p.location, '{STATE_REGEX}', 1) <> ''
            THEN 'other US state'
        ELSE 'state unknown'
    END AS region
FROM postings p
LEFT JOIN (SELECT job_id FROM ({SALARY_SQL})) s ON s.job_id = p.job_id
LEFT JOIN companies c ON c.company_id = p.company_id
"""

n_total, n_disc = con.sql(
    f"SELECT COUNT(*), COUNT(*) FILTER (WHERE disclosed) FROM ({BASE})"
).fetchall()[0]
n_non = n_total - n_disc
print(f"Postings: {n_total:,}   disclosing a salary: {n_disc:,} ({n_disc / n_total:.1%})")


def compare(column: str, title: str) -> None:
    """Disclosure rate per group, and how differently disclosers and non-disclosers are spread."""
    rows = con.sql(f"""
        SELECT {column}, COUNT(*), COUNT(*) FILTER (WHERE disclosed)
        FROM ({BASE})
        GROUP BY {column}
        ORDER BY COUNT(*) DESC
    """).fetchall()
    print(f"\n{title}")
    print(f"   {'group':24s} {'n':>8s} {'disclosed':>10s} {'share among':>12s} {'share among':>12s}")
    print(f"   {'':24s} {'':>8s} {'rate':>10s} {'disclosers':>12s} {'non-discl.':>12s}")
    tvd = 0.0
    for group, n, n_group_disc in rows:
        share_disc = n_group_disc / n_disc
        share_non = (n - n_group_disc) / n_non
        tvd += abs(share_disc - share_non)
        print(f"   {str(group)[:24]:24s} {n:>8,} {n_group_disc / n:>10.1%} {share_disc:>12.1%} {share_non:>12.1%}")
    print(f"   total variation distance: {tvd / 2:.3f}")


compare("experience", "Experience level")
compare("work_type", "Work type")
compare("company_size_group", "Company size (0 smallest - 7 largest)")
compare("region", "Location")

# --- Does pay itself differ by region? (plausible salaries only, D-003) ----
rows = con.sql(f"""
    SELECT
        b.region,
        COUNT(*),
        median(s.annual_salary),
        avg(CASE WHEN s.annual_salary >= {BENCHMARK} THEN 1 ELSE 0 END)
    FROM ({SALARY_SQL}) s
    JOIN ({BASE}) b ON b.job_id = s.job_id
    WHERE s.salary_quality = 'ok'
    GROUP BY b.region
    ORDER BY COUNT(*) DESC
""").fetchall()
print("\nPlausible salaries by location")
print(f"   {'region':24s} {'n':>8s} {'median':>10s} {'>=100k':>8s}")
for region, n, median, share in rows:
    print(f"   {region:24s} {n:>8,} {median:>10,.0f} {share:>8.1%}")