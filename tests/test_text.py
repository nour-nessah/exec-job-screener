"""Unit tests for text cleaning (src/exec_screener/text.py), decision D-006."""
import pytest

from exec_screener.text import strip_salary_amounts


@pytest.mark.parametrize(
    "text, must_not_contain",
    [
        ("Salary Range $44,770.00 - $50,550.80 Salary/year", ["44", "50,550"]),
        ("$115,000.00 To 170,000.00 Annually", ["115", "170"]),  # range end without $
        ("Pay Rate:$175,000- $195,000/yr", ["175", "195"]),
        ("Compensation: $150k plus bonus", ["150"]),
        ("Base salary 95.5K-120K", ["95", "120"]),  # amounts without $
        ("$31.50 per hour", ["31"]),
        ("Sign-on bonus of $10,000!", ["10,000"]),  # over-stripping is intended
    ],
)
def test_amounts_are_removed(text, must_not_contain):
    cleaned = strip_salary_amounts(text)
    for fragment in must_not_contain:
        assert fragment not in cleaned


@pytest.mark.parametrize(
    "text",
    [
        "Founded in 2004, we serve clients in 30 countries.",
        "Requires 5+ years of experience and a 401(k) plan.",
        "Senior Director of Finance",
    ],
)
def test_ordinary_text_is_kept(text):
    assert strip_salary_amounts(text) == text


def test_none_becomes_empty_string():
    assert strip_salary_amounts(None) == ""