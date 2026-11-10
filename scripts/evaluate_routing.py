"""Review routing (D-011): choose thresholds WITHOUT touching the test set, then evaluate them on it.

1. Out-of-fold probabilities on the training companies (grouped 5-fold cross-validation).
2. Thresholds chosen on those, so that automatic decisions are >= 95% correct.
3. Applied to the untouched test set: queue sizes, accuracy, per region, workload curve.
4. A short review list of postings where the model strongly disagrees with the stated salary.

Run from the project root (after scripts/train_model.py):
    python scripts/evaluate_routing.py
"""
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, cross_val_predict

from exec_screener.dataset import load_labelled
from exec_screener.model import build_model, prepare_features
from exec_screener.routing import ACCEPT, REJECT, REVIEW, choose_thresholds, route

DB_PATH = Path("data/processed/linkedin.duckdb")
PREDICTIONS_PATH = Path("data/processed/test_predictions.csv")
REVIEW_LIST_PATH = Path("data/processed/label_review_queue.csv")
FIGURE_PATH = Path("reports/figures/workload.png")
TARGET = 0.95
CURVE_TARGETS = [0.85, 0.875, 0.90, 0.925, 0.95, 0.96, 0.97, 0.98, 0.99]

MODEL_COLOR = "#2a78d6"
TEXT, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"

# --- 1. Out-of-fold probabilities on the training companies ------------------
con = duckdb.connect(str(DB_PATH), read_only=True)
df = load_labelled(con)
train = df[~df["is_test"]]
oof_probability = cross_val_predict(
    build_model(),
    prepare_features(train),
    train["label"].astype(bool),
    groups=train["group"],
    cv=GroupKFold(n_splits=5),
    method="predict_proba",
)[:, 1]
oof_truth = train["label"].astype(bool).to_numpy()

# --- 2. Thresholds, chosen on training data only ----------------------------
t_low, t_high = choose_thresholds(oof_probability, oof_truth, target=TARGET)
print(f"Thresholds for >= {TARGET:.0%} correct automatic decisions (chosen on training folds):")
print(f"   auto-reject if probability <= {t_low:.3f}   auto-accept if probability >= {t_high:.3f}\n")

# --- 3. Apply to the untouched test set --------------------------------------
test = pd.read_csv(PREDICTIONS_PATH)
truth = test["label"].astype(bool).to_numpy()
test["queue"] = route(test["probability"], t_low, t_high)

print(f"Test set ({len(test):,} postings from unseen companies)")
print(f"   {'queue':14s} {'postings':>9s} {'share':>7s} {'truly >= $100k':>15s}")
for queue in [ACCEPT, REVIEW, REJECT]:
    in_queue = (test["queue"] == queue).to_numpy()
    print(f"   {queue:14s} {in_queue.sum():>9,} {in_queue.mean():>7.1%} {truth[in_queue].mean():>15.1%}")
rejected = (test["queue"] == REJECT).to_numpy()
print(f"   -> decided automatically: {(test['queue'] != REVIEW).mean():.1%}; "
      f"$100k+ jobs lost in auto-reject: {truth[rejected].sum() / truth.sum():.1%}\n")

print("Per region")
print(f"   {'region':24s} {'postings':>9s} {'automated':>10s} {'accept correct':>15s} {'reject correct':>15s}")
for region, group in test.groupby("region"):
    labels = group["label"].astype(bool)
    accepted, rejected_g = group["queue"] == ACCEPT, group["queue"] == REJECT
    print(f"   {region:24s} {len(group):>9,} {(group['queue'] != REVIEW).mean():>10.1%} "
          f"{labels[accepted].mean():>15.1%} {(~labels[rejected_g]).mean():>15.1%}")

# --- Workload curve: stricter accuracy target -> more human review -------------
print("\nWorkload curve (thresholds from training folds, measured on test)")
print(f"   {'target':>7s} {'automated':>10s} {'accept correct':>15s} {'reject correct':>15s}")
automated_shares = []
for target in CURVE_TARGETS:
    low, high = choose_thresholds(oof_probability, oof_truth, target=target)
    queues = route(test["probability"], low, high)
    accepted, rejected_t = queues == ACCEPT, queues == REJECT
    automated = (queues != REVIEW).mean()
    automated_shares.append(automated)
    print(f"   {target:>7.1%} {automated:>10.1%} {truth[accepted].mean():>15.1%} {(~truth[rejected_t]).mean():>15.1%}")

fig, ax = plt.subplots(figsize=(6, 4.2), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
ax.plot([t * 100 for t in CURVE_TARGETS], [a * 100 for a in automated_shares], color=MODEL_COLOR,
        linewidth=2, marker="o", markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
chosen = CURVE_TARGETS.index(TARGET)
ax.annotate(f"chosen: {TARGET:.0%} correct → {automated_shares[chosen]:.0%} automated",
            (TARGET * 100, automated_shares[chosen] * 100), xytext=(-10, -4),
            textcoords="offset points", ha="right", va="top", fontsize=8, color=TEXT)
ax.set_xlabel("Required accuracy of automatic decisions (%)", color=TEXT)
ax.set_ylabel("Postings decided without a person (%)", color=TEXT)
ax.set_title("Stricter accuracy means more human review", loc="left", fontsize=11, color=TEXT)
ax.set_ylim(0, 100)
ax.grid(color=GRID, linewidth=0.8)
ax.tick_params(colors=MUTED, labelsize=8)
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
for side in ["left", "bottom"]:
    ax.spines[side].set_color(GRID)
FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGURE_PATH, bbox_inches="tight", facecolor=SURFACE)

# --- 4. Review list: model strongly disagrees with the stated salary -------------
disagree = ((test["probability"] >= 0.95) & ~test["label"].astype(bool)) | (
    (test["probability"] <= 0.05) & test["label"].astype(bool)
)
review_list = test[disagree].sort_values("probability")
review_list.to_csv(REVIEW_LIST_PATH, index=False)
print(f"\nLabel review list: {len(review_list)} postings ({disagree.mean():.1%} of test) "
      f"-> {REVIEW_LIST_PATH}")
print(f"Saved figure to {FIGURE_PATH}")