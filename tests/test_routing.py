"""Unit tests for review routing (src/exec_screener/routing.py), decision D-011."""
import numpy as np

from exec_screener.routing import ACCEPT, REJECT, REVIEW, choose_thresholds, route

# 10 hand-made postings, sorted by probability; True = truly >= $100k.
PROBABILITY = [0.02, 0.05, 0.10, 0.20, 0.40, 0.55, 0.70, 0.85, 0.90, 0.97]
TRUTH = [False, False, False, True, False, True, False, True, True, True]


def test_thresholds_on_hand_made_example():
    # Top 3 (0.97, 0.90, 0.85) are all positive; adding 0.70 (negative) drops precision to 75%.
    # Bottom 3 (0.02, 0.05, 0.10) are all negative; adding 0.20 (positive) drops it to 75%.
    assert choose_thresholds(PROBABILITY, TRUTH, target=0.95) == (0.10, 0.85)


def test_lower_target_automates_more():
    t_low, t_high = choose_thresholds(PROBABILITY, TRUTH, target=0.75)
    assert t_low >= 0.10 and t_high <= 0.85


def test_route_assigns_three_queues():
    queues = route([0.05, 0.50, 0.95], t_low=0.10, t_high=0.85)
    assert list(queues) == [REJECT, REVIEW, ACCEPT]


def test_boundaries_are_automatic():
    queues = route([0.10, 0.85], t_low=0.10, t_high=0.85)
    assert list(queues) == [REJECT, ACCEPT]


def test_impossible_target_sends_everything_to_review():
    t_low, t_high = choose_thresholds([0.3, 0.6], [True, False], target=0.99)
    assert list(route([0.3, 0.6], t_low, t_high)) == [REVIEW, REVIEW]