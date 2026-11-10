"""Where does the model fail, and why?

Subgroups (D-004, D-005), errors near the benchmark, most confident mistakes, strongest words.
Reads data/processed/test_predictions.csv and models/model.joblib (no retraining).
Run from the project root:
    python scripts/error_analysis.py
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from exec_screener.salary import BENCHMARK

PREDICTIONS_PATH = Path("data/processed/test_predictions.csv")
MODEL_PATH = Path("models/model.joblib")
THRESHOLD = 0.5
MARGIN = 10_000  # "near the benchmark" = within $10k of $100k

df = pd.read_csv(PREDICTIONS_PATH)
truth = df["label"].astype(bool).to_numpy()
flagged = (df["probability"] >= THRESHOLD).to_numpy()
salary = df["annual_salary"].to_numpy()


def scores(mask: np.ndarray):
    """(postings, share positive, precision, recall, F1) within a subgroup."""
    t, f = truth[mask], flagged[mask]
    tp, fp, fn = int((t & f).sum()), int((~t & f).sum()), int((t & ~f).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
    return int(mask.sum()), t.mean(), precision, recall, f1


# --- 1. Subgroups -------------------------------------------------------------
hourly = (df["pay_period"] == "HOURLY").to_numpy()
subgroups = {
    "all test postings": np.ones(len(df), dtype=bool),
    **{f"region: {region}": (df["region"] == region).to_numpy() for region in sorted(df["region"].unique())},
    "hourly contract (D-004)": hourly & (df["work_type"] == "CONTRACT").to_numpy(),
    "hourly full-time": hourly & (df["work_type"] == "FULL_TIME").to_numpy(),
    "yearly pay": (df["pay_period"] == "YEARLY").to_numpy(),
    "experience level missing": (df["experience"] == "missing").to_numpy(),
}
print(f"1. Performance by subgroup (threshold {THRESHOLD})")
print(f"   {'subgroup':32s} {'postings':>8s} {'positive':>9s} {'precision':>10s} {'recall':>7s} {'F1':>6s}")
for name, mask in subgroups.items():
    n, positive, precision, recall, f1 = scores(mask)
    print(f"   {name:32s} {n:>8,} {positive:>9.1%} {precision:>10.1%} {recall:>7.1%} {f1:>6.3f}")

# --- 2. Are errors concentrated near the benchmark? -------------------------
false_pos, false_neg = ~truth & flagged, truth & ~flagged
near_below = salary >= BENCHMARK - MARGIN
near_above = salary < BENCHMARK + MARGIN
print(f"\n2. Errors near the ${BENCHMARK:,} line (within ${MARGIN:,})")
print(f"   false positives ({false_pos.sum():,}) paying ${BENCHMARK - MARGIN:,}-{BENCHMARK:,}: "
      f"{near_below[false_pos].mean():.1%}   (all negatives: {near_below[~truth].mean():.1%})")
print(f"   false negatives ({false_neg.sum():,}) paying ${BENCHMARK:,}-{BENCHMARK + MARGIN:,}: "
      f"{near_above[false_neg].mean():.1%}   (all positives: {near_above[truth].mean():.1%})")


# --- 3. The most confident mistakes -----------------------------------------
def show(rows: pd.DataFrame, heading: str) -> None:
    print(f"\n{heading}")
    for _, row in rows.iterrows():
        print(f"   {row['probability']:.3f}  {str(row['title'])[:48]:48s} "
              f"{row['annual_salary']:>9,.0f}  {row['pay_period']:7s} {row['work_type']}")


show(df[false_pos].nlargest(6, "probability"), "3. Most confident FALSE POSITIVES (model sure it is >= $100k)")
show(df[false_neg].nsmallest(6, "probability"), "4. Most confident FALSE NEGATIVES (model sure it is < $100k)")

# --- 5. Strongest words -------------------------------------------------------
model = joblib.load(MODEL_PATH)
names = model.named_steps["features"].get_feature_names_out()
weights = model.named_steps["classifier"].coef_[0]
order = np.argsort(weights)
print("\n5. Features pushing TOWARDS >= $100k          | features pushing AWAY from it")
for up, down in zip(order[::-1][:12], order[:12]):
    print(f"   {weights[up]:+.2f} {names[up]:38s} | {weights[down]:+.2f} {names[down]}")