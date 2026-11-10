"""Tests for single-posting explanations (src/exec_screener/explain.py).

They need a trained model and are skipped if it has not been built yet.
"""
import math
from pathlib import Path

import joblib
import pandas as pd
import pytest

from exec_screener.explain import explain
from exec_screener.model import prepare_features
from exec_screener.routing import REVIEW

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "model.joblib"

pytestmark = pytest.mark.skipif(
    not MODEL_PATH.exists(), reason="model not trained: run python scripts/train_model.py"
)

VP = {
    "title": "Vice President of Finance",
    "description": "Lead our finance team. 10 years of experience in corporate finance required.",
    "region": "other US state",
    "work_type": "FULL_TIME",
    "experience": "Executive",
}
SUPPORT = {
    "title": "Customer Service Representative",
    "description": "Assist customers by phone. High school diploma required. Daily tasks.",
    "region": "other US state",
    "work_type": "FULL_TIME",
    "experience": "Entry level",
}


@pytest.fixture(scope="module")
def model():
    return joblib.load(MODEL_PATH)


def test_contributions_add_up_to_log_odds(model):
    result = explain(model, VP, t_low=0.2, t_high=0.8)
    log_odds = math.log(result.probability / (1 - result.probability))
    assert result.intercept + result.contributions["contribution"].sum() == pytest.approx(log_odds, abs=1e-6)


def test_probability_matches_the_model(model):
    result = explain(model, VP, t_low=0.2, t_high=0.8)
    expected = model.predict_proba(prepare_features(pd.DataFrame([VP])))[0, 1]
    assert result.probability == pytest.approx(expected)


def test_senior_posting_scores_higher_than_entry_level(model):
    assert explain(model, VP, 0.2, 0.8).probability > explain(model, SUPPORT, 0.2, 0.8).probability


def test_queue_uses_the_thresholds(model):
    # Thresholds that can never be reached send every posting to review.
    assert explain(model, VP, t_low=-1.0, t_high=2.0).queue == REVIEW