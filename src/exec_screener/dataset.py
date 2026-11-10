"""Modelling dataset: labelled postings with features, and a deterministic company-grouped split.

Decisions: target and metrics D-007, region feature D-005, grouped split D-008.
"""
import hashlib

import pandas as pd

from exec_screener.salary import BENCHMARK, SALARY_SQL

# D-005: US states requiring salary ranges in job postings during 2023-2024.
PAY_TRANSPARENCY_STATES = ("CA", "CO", "NY", "WA")
STATE_REGEX = r",\s*([A-Z]{2})$"  # "San Francisco, CA" -> "CA"

REGION_SQL = f"""
    CASE
        WHEN regexp_extract(location, '{STATE_REGEX}', 1) IN {PAY_TRANSPARENCY_STATES}
            THEN 'pay-transparency state'
        WHEN regexp_extract(location, '{STATE_REGEX}', 1) <> ''
            THEN 'other US state'
        ELSE 'state unknown'
    END
"""

# D-007: one row per labelled posting (plausible salaries only), with the model's inputs.
LABELLED_SQL = f"""
SELECT
    job_id,
    company_id,
    company_name,
    title,
    description,
    work_type,
    COALESCE(formatted_experience_level, 'missing') AS experience,
    {REGION_SQL} AS region,
    annual_salary,
    annual_salary >= {BENCHMARK} AS label
FROM ({SALARY_SQL})
WHERE salary_quality = 'ok'
ORDER BY job_id
"""

TEST_PERCENT = 20


def group_key(company_id, company_name, job_id) -> str:
    """Key that keeps all postings of one company together (D-008)."""
    if pd.notna(company_id):
        return f"company:{int(company_id)}"
    if isinstance(company_name, str) and company_name.strip():
        return f"name:{company_name.strip().lower()}"
    return f"job:{job_id}"


def is_test(key: str, test_percent: int = TEST_PERCENT) -> bool:
    """Deterministic split: the same key always lands in the same split, on every machine."""
    bucket = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16) % 100
    return bucket < test_percent


def load_labelled(con) -> pd.DataFrame:
    """Labelled postings as a DataFrame, with a company group key and the test-split flag."""
    relation = con.sql(LABELLED_SQL)
    df = pd.DataFrame(relation.fetchall(), columns=relation.columns)
    df["group"] = [
        group_key(company_id, name, job_id)
        for company_id, name, job_id in zip(df["company_id"], df["company_name"], df["job_id"])
    ]
    df["is_test"] = df["group"].map(is_test)
    return df