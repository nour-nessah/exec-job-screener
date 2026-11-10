"""Precision-recall curve of the model vs the keyword baselines, on the same test split.

Reads the predictions written by scripts/train_model.py (no retraining).
Run from the project root:
    python scripts/plot_pr_curve.py
"""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw to a file, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_curve

from exec_screener.baseline import EXEC_TITLE_PATTERN, SENIOR_TITLE_PATTERN

PREDICTIONS_PATH = Path("data/processed/test_predictions.csv")
FIGURE_PATH = Path("reports/figures/pr_curve.png")

# Colours: categorical slots 1-3 of a colour-blind-checked palette; text in neutral inks.
MODEL_COLOR, EXEC_COLOR, SENIOR_COLOR = "#2a78d6", "#eb6834", "#1baf7a"
TEXT, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"

df = pd.read_csv(PREDICTIONS_PATH)
truth = df["label"].astype(bool).to_numpy()
probability = df["probability"].to_numpy()
titles = df["title"].fillna("")

precision, recall, thresholds = precision_recall_curve(truth, probability)
average_precision = average_precision_score(truth, probability)


def rule_point(pattern: str):
    """(precision, recall) of a keyword rule on the same test postings."""
    flagged = np.array([bool(re.search(pattern, title)) for title in titles])
    tp = (flagged & truth).sum()
    return tp / flagged.sum(), tp / truth.sum()


rules = {
    "Title: executive keywords": (rule_point(EXEC_TITLE_PATTERN), EXEC_COLOR),
    "Title: executive + senior keywords": (rule_point(SENIOR_TITLE_PATTERN), SENIOR_COLOR),
}

# --- Numbers --------------------------------------------------------------
f1 = 2 * precision[:-1] * recall[:-1] / np.clip(precision[:-1] + recall[:-1], 1e-12, None)
best = int(np.argmax(f1))
print(f"Test postings: {len(df):,}   positive: {truth.mean():.1%}")
print(f"Average precision (area under the PR curve): {average_precision:.3f}")
print(f"Best F1: {f1[best]:.3f} at threshold {thresholds[best]:.2f} "
      f"(precision {precision[best]:.1%}, recall {recall[best]:.1%})\n")

print(f"{'baseline':36s} {'precision':>10s} {'recall':>7s} | {'model precision':>16s} {'model recall':>13s}")
print(f"{'':36s} {'':>10s} {'':>7s} | {'at same recall':>16s} {'at same prec.':>13s}")
for name, ((rule_precision, rule_recall), _) in rules.items():
    model_precision = precision[recall >= rule_recall].max()
    model_recall = recall[precision >= rule_precision].max()
    print(f"{name:36s} {rule_precision:>10.1%} {rule_recall:>7.1%} | {model_precision:>16.1%} {model_recall:>13.1%}")

# --- Figure ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 5), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ax.plot(recall, precision, color=MODEL_COLOR, linewidth=2,
        label=f"Model (average precision {average_precision:.2f})")
for name, ((rule_precision, rule_recall), color) in rules.items():
    ax.scatter(rule_recall, rule_precision, s=80, color=color, edgecolors=SURFACE,
               linewidths=2, zorder=3, label=name)
    ax.annotate(name.replace("Title: ", ""), (rule_recall, rule_precision), xytext=(9, 0),
                textcoords="offset points", va="center", fontsize=8, color=TEXT)
ax.axhline(truth.mean(), color=MUTED, linewidth=1, linestyle="--")
ax.text(0.99, truth.mean() + 0.015, f"no skill (share of jobs ≥ $100k: {truth.mean():.0%})",
        ha="right", va="bottom", fontsize=8, color=MUTED)

ax.set_xlim(0, 1)
ax.set_ylim(0, 1.02)
ax.set_xlabel("Recall: share of $100k+ jobs found", color=TEXT)
ax.set_ylabel("Precision: share of flagged jobs truly $100k+", color=TEXT)
ax.set_title("Model vs keyword rules on companies not seen in training",
             loc="left", fontsize=11, color=TEXT)
ax.grid(color=GRID, linewidth=0.8)
ax.tick_params(colors=MUTED, labelsize=8)
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
for side in ["left", "bottom"]:
    ax.spines[side].set_color(GRID)
ax.legend(loc="lower left", fontsize=8, frameon=False, labelcolor=TEXT)

FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGURE_PATH, bbox_inches="tight", facecolor=SURFACE)
print(f"\nSaved figure to {FIGURE_PATH}")