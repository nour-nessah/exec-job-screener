"""Unit tests for the shared salary rules (src/exec_screener/salary.py).

Each test builds a tiny, hand-made postings table in an in-memory database,
runs the real SALARY_SQL on it, and checks the result against values computed by hand.
"""
import duckdb
import pytest

from exec_screener.salary import ANNUAL_FACTORS, CEILING, FLOOR, SALARY_SQL


def run_salary_sql(rows):
    """Run SALARY_SQL on hand-made postings.

    rows: list of (job_id, pay_period, min_salary, med_salary, max_salary)
    returns: {job_id: (point_method, annual_salary, salary_quality)}
    """
    con = duckdb.connect()  # in-memory: nothing touches the real database
    con.execute("""
        CREATE TABLE postings (
            job_id INTEGER,
            pay_period VARCHAR,
            min_salary DOUBLE,
            med_salary DOUBLE,
            max_salary DOUBLE
        )
    """)
    for row in rows:
        con.execute("INSERT INTO postings VALUES (?, ?, ?, ?, ?)", row)
    result = con.sql(f"""
        SELECT job_id, point_method, annual_salary, salary_quality
        FROM ({SALARY_SQL})
    """).fetchall()
    return {job_id: (method, annual, quality) for job_id, method, annual, quality in result}


def test_range_uses_midpoint():
    result = run_salary_sql([(1, "YEARLY", 100_000, None, 120_000)])
    assert result[1] == ("range midpoint", 110_000, "ok")


def test_median_used_when_no_range():
    result = run_salary_sql([(1, "HOURLY", None, 50, None)])
    assert result[1] == ("median only", 50 * 2080, "ok")


@pytest.mark.parametrize("period, factor", ANNUAL_FACTORS.items())
def test_annualisation_factor(period, factor):
    result = run_salary_sql([(1, period, None, 1_000, None)])
    assert result[1][1] == 1_000 * factor


def test_postings_without_salary_are_excluded():
    result = run_salary_sql([(1, "YEARLY", 100_000, None, 120_000), (2, None, None, None, None)])
    assert set(result) == {1}


@pytest.mark.parametrize(
    "pay_period, med_salary, expected_quality",
    [
        ("HOURLY", 5, "below_floor"),          # $10,400 a year: below minimum wage
        ("HOURLY", 7.25, "ok"),                # exactly the floor ($15,080) is allowed
        ("YEARLY", CEILING, "ok"),             # exactly the ceiling is allowed
        ("HOURLY", 125_000, "above_ceiling"),  # a yearly salary mislabelled as hourly
        ("DAILY", 500, "unknown_period"),      # a pay period we have no factor for
    ],
)
def test_quality_flag(pay_period, med_salary, expected_quality):
    result = run_salary_sql([(1, pay_period, None, med_salary, None)])
    assert result[1][2] == expected_quality


def test_floor_is_minimum_wage_full_time():
    assert FLOOR == 15_080