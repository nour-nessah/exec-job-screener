"""Unit tests for the title-keyword baselines (src/exec_screener/baseline.py)."""
import re

import pytest

from exec_screener.baseline import EXEC_TITLE_PATTERN, SENIOR_TITLE_PATTERN


@pytest.mark.parametrize(
    "title, is_exec, is_senior",
    [
        ("Chief Financial Officer", True, True),
        ("CFO", True, True),
        ("VP, Sales", True, True),
        ("Head of Data Science", True, True),
        ("Director of Finance", True, True),
        ("Senior Software Engineer", False, True),
        ("Sr. Accountant", False, True),
        ("Project Manager", False, True),
        ("Software Engineer", False, False),
        ("Cashier", False, False),
        ("Directory Assistant", False, False),  # word boundary: "directory" is not "director"
    ],
)
def test_title_patterns(title, is_exec, is_senior):
    assert bool(re.search(EXEC_TITLE_PATTERN, title)) is is_exec
    assert bool(re.search(SENIOR_TITLE_PATTERN, title)) is is_senior