"""Data-quality tests on the real database.

Unit tests (test_salary.py) check the code on hand-made inputs with exact values.
These tests check the real data with invariants and tolerances, so they keep working
when the data is legitimately refreshed. Skipped if the database has not been built.
"""
from pathlib import Path

import duckdb
import pytest

from exec_screener.salary import SALARY_SQL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "linkedin.duckdb"

pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason="database not built: run python scripts/build_db.py"
)


@pytest.fixture(scope="module")
def con():
    """One read-only connection shared by all tests in this file."""
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


def scalar(con, sql: str):
    """Run a query that returns a single value, and return that value."""
    return con.sql(sql).fetchall()[0][0]


@pytest.mark.parametrize(
    "table, key",
    [("postings", "job_id"), ("salaries", "job_id"), ("companies", "company_id")],
)
def test_primary_key_is_unique_and_complete(con, table, key):
    n_rows, n_unique, n_missing = con.sql(
        f"SELECT COUNT(*), COUNT(DISTINCT {key}), COUNT(*) - COUNT({key}) FROM {table}"
    ).fetchall()[0]
    assert n_missing == 0
    assert n_unique == n_rows


def test_every_pay_period_has_a_factor(con):
    n_unknown = scalar(
        con, f"SELECT COUNT(*) FROM ({SALARY_SQL}) WHERE salary_quality = 'unknown_period'"
    )
    assert n_unknown == 0


def test_annual_salary_matches_dataset_normalized_salary(con):
    n_mismatch = scalar(
        con,
        f"SELECT COUNT(*) FROM ({SALARY_SQL}) WHERE abs(annual_salary - normalized_salary) > 0.01",
    )
    assert n_mismatch == 0


def test_share_of_implausible_salaries_stays_small(con):
    share = scalar(
        con,
        f"SELECT avg(CASE WHEN salary_quality <> 'ok' THEN 1 ELSE 0 END) FROM ({SALARY_SQL})",
    )
    assert share < 0.02  # currently 1.39% (D-003); a jump would signal a new data problem


@pytest.mark.xfail(
    strict=True,
    reason="Known source issue: 4,712 salary rows reference job_ids missing from postings "
    "(see scripts/check_keys.py)",
)
def test_every_salary_row_has_a_posting(con):
    n_orphans = scalar(
        con,
        """
        SELECT COUNT(*) FROM salaries s
        WHERE NOT EXISTS (SELECT 1 FROM postings p WHERE p.job_id = s.job_id)
        """,
    )
    assert n_orphans == 0