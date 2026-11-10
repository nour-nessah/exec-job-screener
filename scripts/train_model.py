"""Train the screening model on the training split and evaluate it on the test split.

Run from the project root:
    python scripts/train_model.py
"""
import re
import time
from pathlib import Path

import duckdb
import joblib
import numpy as np

from exec_screener.baseline import EXEC_TITLE_PATTERN, SENIOR_TITLE_PATTERN
from exec_screener.dataset import load_labelled
from exec_screener.model import build_model, prepare_features

DB_PATH = Path("data/processed/linkedin.duckdb")
MODEL_PATH = Path("models/model.joblib")
PREDICTIONS_PATH = Path("data/processed/test_predictions.csv")
PREDICTION_COLUMNS = [
    "job_id", "title", "region", "work_type", "pay_period", "experience", "annual_salary", "label",
]

con = duckdb.connect(str(DB_PATH), read_only=True)
df = load_labelled(con)
X = prepare_features(df)
y = df["label"].astype(bool)
train, test = ~df["is_test"], df["is_test"]

model = build_model()
start = time.perf_counter()
model.fit(X[train], y[train])
seconds = time.perf_counter() - start
n_features = len(model.named_steps["features"].get_feature_names_out())

probability = model.predict_proba(X[test])[:, 1]
truth = y[test].to_numpy()


def scores(flagged: np.ndarray):
    """(flagged, precision, recall, F1) of a yes/no prediction on the test set."""
    tp = int((flagged & truth).sum())
    fp = int((flagged & ~truth).sum())
    fn = int((~flagged & truth).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
    return int(flagged.sum()), precision, recall, f1


titles = df.loc[test, "title"].fillna("")
predictions = {
    "title: executive keywords": np.array([bool(re.search(EXEC_TITLE_PATTERN, t)) for t in titles]),
    "title: executive + senior keywords": np.array([bool(re.search(SENIOR_TITLE_PATTERN, t)) for t in titles]),
    "model (probability >= 0.5)": probability >= 0.5,
}

print(f"Training postings: {train.sum():,}   test postings: {test.sum():,} (company-grouped split, D-008)")
print(f"Features: {n_features:,}   training time: {seconds:.1f} s\n")
print(f"Test set                              {'flagged':>7s} {'precision':>10s} {'recall':>7s} {'F1':>6s}")
for name, flagged in predictions.items():
    n_flagged, precision, recall, f1 = scores(flagged)
    print(f"   {name:34s} {n_flagged:>7,} {precision:>10.1%} {recall:>7.1%} {f1:>6.3f}")

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL_PATH)
results = df.loc[test, PREDICTION_COLUMNS].copy()
results["probability"] = probability
results.to_csv(PREDICTIONS_PATH, index=False)
print(f"\nSaved model to {MODEL_PATH} and test predictions to {PREDICTIONS_PATH}")