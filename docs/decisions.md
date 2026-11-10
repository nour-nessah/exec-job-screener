# Decision Log

Key analytical decisions, with the evidence behind them and the alternatives considered.
Numbers refer to the Kaggle "LinkedIn Job Postings (2023–2024)" dataset (123,849 postings).

---

## D-001 — One point estimate per salary: range midpoint, else median

**Context.** 36,073 postings disclose a salary. Each gives either a range
(min and max: 29,793 postings) or a single median (6,280), never both.

**Decision.** Use `(min + max) / 2` when a range exists, otherwise the median.

**Alternatives considered.**
- *Maximum*: best-case figure; biases salaries upwards and inflates the share of jobs ≥ $100k.
- *Minimum*: the opposite bias.

**Consequences.** One comparable number per posting. Our annualised values reproduce
the dataset's `normalized_salary` exactly (0 differences above $0.01 on 36,073 rows),
which confirms how that column was built.

---

## D-002 — Annualisation factors and plausibility band

**Context.** Salaries are stated per hour, week, two weeks, month or year.

**Decision.** Multiply by 2,080 (hourly: 40 h × 52 weeks), 52 (weekly), 26 (biweekly),
12 (monthly) or 1 (yearly). Then flag annual salaries outside a plausibility band:
- **Floor: $15,080** = US federal minimum wage ($7.25) × 2,080 hours. A full-time salary
  below the legal minimum is almost certainly a data error.
- **Ceiling: $1,000,000**, a generous upper bound for a single base salary, far above
  typical executive base pay so that real senior salaries are not flagged.

**Consequences.** 500 of 36,073 salaries (1.39%) fall outside the band.
The hourly factor assumes full-time, full-year work; this assumption is tested separately
(see D-004, pending).

---

## D-003 — Implausible salaries: flag and quarantine, do not delete or auto-correct

**Context.** Inspecting raw values showed that in most implausible rows the number is
plausible but the pay-period **unit** is wrong:
- 6 of 9 "biweekly" salaries are yearly amounts ($54k–90k), inflated ×26 to $1.5–2.1M.
- 29 "hourly" rates are ≥ $1,000 (e.g. $240k–275k "per hour"), i.e. yearly salaries.
- 382 "yearly" values lie between $0 and $1,000, mostly hourly rates (e.g. $20–24).

Some cases are genuinely ambiguous: "Principal Backend Engineer, 200–225, yearly" could be
$200/hour (≈ $440k/year) or $200k–225k written in thousands.

**Decision.** Keep every row and add a quality flag
(`ok`, `below_floor`, `above_ceiling`). Train and evaluate models only on `ok` rows.
Flagged rows form a queue for human review.

**Alternatives considered.**
- *Delete the rows*: silent information loss; the problem can no longer be counted or reviewed.
- *Auto-correct the unit*: requires guessing in ambiguous cases, which creates confident but
  possibly wrong labels.

**Consequences.**
- Costs 1.39% of training labels.
- Prevents 38 junior-level postings above $1M from being labelled "executive".
- Share of postings ≥ $100k: 38.80% (all rows) vs 39.24% (plausible rows only).