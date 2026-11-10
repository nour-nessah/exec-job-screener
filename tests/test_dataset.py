"""Unit tests for the company-grouped split (src/exec_screener/dataset.py), decision D-008."""
import math

from exec_screener.dataset import group_key, is_test


def test_group_key_uses_company_id_first():
    assert group_key(167757.0, "Some Name", 1) == "company:167757"


def test_group_key_falls_back_to_company_name():
    assert group_key(None, "  Acme Corp ", 1) == "name:acme corp"


def test_group_key_falls_back_to_job_id():
    assert group_key(math.nan, None, 42) == "job:42"


def test_is_test_is_deterministic():
    assert is_test("company:167757") == is_test("company:167757")


def test_is_test_share_is_close_to_20_percent():
    share = sum(is_test(f"company:{i}") for i in range(10_000)) / 10_000
    assert 0.18 < share < 0.22


def test_is_test_extremes():
    assert not any(is_test(f"k{i}", test_percent=0) for i in range(100))
    assert all(is_test(f"k{i}", test_percent=100) for i in range(100))