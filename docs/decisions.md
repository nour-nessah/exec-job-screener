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
The hourly factor assumes full-time, full-year work; see D-004 for how this is interpreted.

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

---

## D-004 — `annual_salary` means full-time-equivalent pay of the role

**Context.** Converting hourly pay with × 2,080 assumes 40 hours a week, 52 weeks a year.
Among plausible salaries, hourly **contract** jobs reach ≥ $100k in 48.2% of cases,
hourly **full-time** jobs in only 11.5%. Does the conversion inflate contract salaries?

**Evidence.**
- *Composition, not conversion:* the median rate is $47.50/h for hourly contracts vs
  $24.00/h for hourly full-time jobs. These are different kinds of jobs (confounding).
- *Reference group without conversion:* yearly-paid contracts have a median of $100,000 and
  53.1% ≥ $100k; hourly contracts after × 2,080 have $98,800 and 48.2%. No sign of
  systematic inflation (caveat: only 286 yearly-paid contracts).
- *Sensitivity:* hourly contracts supply 1,611 of 13,959 positive labels (11.5%).
  If contractors were paid for 75% of the year, 746 labels (5.3%) would flip;
  at 50%, 1,515 (10.9%).

**Decision.** Keep the factors and define `annual_salary` explicitly as the
**full-time-equivalent (FTE) annual pay of the role**: what the position pays per full-time
year, not what one person earns in a calendar year. This is how salary benchmarks compare
positions. Keep `work_type` as a model feature, and report model performance on hourly
contracts separately.

**Alternatives considered.**
- *Exclude non-full-time hourly jobs* (contract, part-time, temporary): loses 5,626 rows
  (15.8% of plausible salaries), including many genuinely high-paid contractor roles.
- *Apply a utilisation factor* (e.g. 0.75 for contracts): replaces one unverifiable
  assumption with an invented number.

**Consequences.** The label has a clear, documented meaning that matches the dataset's
`normalized_salary`. The remaining uncertainty is quantified: at most 10.9% of positive
labels change under a 50% utilisation scenario.

---

## D-005 — Salary disclosure: treat as missing at random given location

**Context.** Only 36,073 of 123,849 postings (29.1%) disclose a salary, so the model learns
from disclosers but must predict for non-disclosers. Are disclosers representative?

**Evidence** (total variation distance between disclosers and non-disclosers):
- *Location: 0.217.* In pay-transparency states (CA, CO, NY, WA), 50.1% of postings disclose
  a salary vs 22.4% in other US states. These states make up 31.3% of disclosers but only
  12.8% of non-disclosers. Disclosure is driven mainly by law.
- *Experience level: 0.080, company size: 0.075, work type: 0.028.* Smaller differences.
  Directors (33.8%) and Executives (31.3%) disclose more often than average (29.1%):
  no sign that senior roles hide their pay.
- *Pay also differs by region* (plausible salaries): share ≥ $100k is 31.3% in other US
  states, 43.6% in pay-transparency states and 54.8% where no state is given (mostly
  national/remote postings). The gap holds within every experience level.

**Decision.** Assume disclosure is missing at random *given location* (MAR):
- Use region as a model feature, so pay levels are learned per region.
- Evaluate the model per region, especially "other US state", where 73% of
  non-disclosers are located.

**Alternatives considered.**
- *Ignore the bias*: the training data over-represents high-paying regions; the model
  would overestimate jobs in other states.
- *Importance weighting by region*: a valid alternative; kept as a robustness check.

**Residual risk.** If, within a region, the best-paying employers systematically hide salaries
(missing not at random), no observable data can detect it. This limitation is stated
explicitly rather than assumed away.

---

## D-006 — Remove money amounts from descriptions before modelling (target leakage)

**Context.** The label is "annual salary ≥ $100k", and many descriptions state the salary
as text ("Salary Range: $115,000 – $170,000"). A text model could learn to read the answer.

**Evidence.**
- Salary-like amounts appear in 52.9% of disclosers' descriptions (the training data) but
  only 14.4% of non-disclosers' (the population we predict for). Evaluation on disclosers
  would therefore overstate real-world performance.
- In 37% of plausible training examples, the first yearly-style amount in the text alone
  agrees with the label 84% of the time (quick check, no model).
- A dollar amount is not always a salary: e.g. a Registered Nurse posting mentioning
  "$10,000" (most likely a sign-on bonus).

**Decision.** Before any modelling, replace every money-like amount in the description with
a space (`exec_screener.text.strip_salary_amounts`): `$` amounts, comma-separated
thousands (e.g. the end of a range "170,000.00"), and "k" amounts. Over-stripping is
deliberate: removing a harmless number costs little; leaving a salary in costs a lot.

**Verification.**
- 11 unit tests on real-world formats, including text that must stay unchanged
  ("2004", "30 countries", "401(k)").
- On all 123,849 descriptions: matches in disclosers' descriptions drop from
  25,830 / 13,203 / 6,212 (any $ amount / yearly-style / hourly-style) to 0 / 0 / 0.
  51.0% of descriptions are changed (including harmless numbers such as "10,000 employees").

**Alternatives considered.**
- *Remove only amounts identified as salaries*: requires telling salaries from bonuses
  and other amounts, which a regex cannot do reliably; any miss leaks the label.
- *Keep the text and rely on the model*: the model would exploit the leak.

**Opportunity noted.** 12,623 non-disclosers mention a salary-like amount in their text.
Extracting these (with context words and validation) could add up to ~35% more labelled
examples, which is a natural next step for a data-extraction pipeline.

---

## D-007 — Target, evaluation metrics and baselines

**Target.** `label = 1` if the full-time-equivalent annual salary (D-004) is ≥ $100,000,
using plausible salaries only (D-003): 35,573 labelled postings, 13,959 positive (39.2%).

**Metrics.** Accuracy is misleading: always predicting "below benchmark" already reaches
60.8%. We report:
- *Precision*: of the jobs flagged, the share truly ≥ $100k (quality of a premium feed).
- *Recall*: of the jobs truly ≥ $100k, the share found (completeness of the inventory).
- *F1*, and the full precision-recall curve for probabilistic models.

**Baselines** (all labelled postings):

| Rule | Flagged | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Always "below benchmark" | 0 | 60.8% | – | 0.0% | 0.000 |
| Experience = Director/Executive | 1,645 | 64.4% | 89.2% | 10.5% | 0.188 |
| Title: executive keywords | 2,115 | 65.0% | 85.5% | 13.0% | 0.225 |
| Title: executive + senior keywords | 11,909 | 71.0% | 65.3% | 55.7% | 0.601 |

**Findings.**
- Executive titles are precise but rare: most jobs ≥ $100k are senior professional roles
  (controller, project manager, software engineer, tax manager, attorney).
- Keywords ignore context: frequent false alarms include "human resources business partner",
  "executive assistant to chief executive officer" and "assistant director".

**Decision.** A model is only worth its complexity if its precision-recall curve lies above
both keyword-rule points and its best F1 exceeds 0.601. In Phase 3, the baselines are
re-evaluated on exactly the same test split as the model.

---

## D-008 — Company-grouped, deterministic train/test split

**Context.** Companies post near-identical jobs many times (templates for several cities,
re-posts, several openings for one role). With a random split, one copy lands in training
and its twin in the test set, inflating test scores.

**Evidence** (35,573 labelled postings, 10,730 company groups, 20% test target):

| Split | Train | Test | Positive (train / test) | Test postings with an identical twin in training | Companies on both sides |
|---|---|---|---|---|---|
| Random (by posting) | 28,416 | 7,157 | 39.1% / 39.9% | 486 (6.8%) | 2,200 |
| Grouped (by company) | 29,148 | 6,425 | 39.4% / 38.5% | 9 (0.1%) | 0 |

The 9 remaining twins are identical texts posted by *different* companies (e.g. staffing
agencies reusing templates).

**Decision.**
- Group key: `company_id`; if missing, the normalised company name; if also missing, the
  posting itself (497 labelled postings have neither).
- Assign a group to the test set if `md5(group key) mod 100 < 20`. The assignment is
  deterministic (no random seed to store), identical on every machine, and stable when
  new data arrives. Python's built-in `hash()` is not used because it is randomised per
  process.

**Consequences.** The test set measures performance on **companies the model has never
seen**, the realistic situation for new crawled sources. The test share is 18.1% of
postings because a few large employers fell into training; the label balance is preserved.

---

## D-009 — Model evaluation: ranking quality and calibration (no recalibration)

**Ranking** (test set: 6,425 postings from companies not seen in training, 38.5% positive):
- Average precision 0.909 (no-skill level: 0.385). Best F1 0.833 at threshold 0.43.
- The model dominates both keyword rules: at the senior-keyword rule's recall (57.5%) it is
  93% precise (rule: 64%); at the same precision (64%) it finds 97% of $100k+ jobs
  (rule: 57.5%). At the executive rule's recall (13.9%) it is 99.3% precise.

**Calibration.**
- Brier score 0.096 (always predicting the base rate: 0.237).
- Expected calibration error 0.024; no probability bin is off by more than ~4.5 points.
- Mild, typical pattern for regularised logistic regression: slightly too cautious at the
  extremes (predicted 95% → observed 97%; predicted 4% → observed 1.5%).
- Calibrated within each region: "other US state" 31.5% predicted vs 31.0% observed, where
  73% of non-disclosers are located. This supports D-005 (region as a feature).

**Decision.** Use the probabilities as they are. Recalibration (e.g. isotonic regression)
would require a separate calibration set taken from the training data, for a gain of at
most a few points.

---

## D-010 — Error analysis: subgroups, label noise and the realistic performance figure

**Subgroups** (test set, threshold 0.5):

| Subgroup | Postings | Positive | Precision | Recall | F1 |
|---|---|---|---|---|---|
| All test postings | 6,425 | 38.5% | 82.5% | 82.1% | 0.823 |
| Region: other US state | 3,355 | 31.0% | 79.8% | 76.5% | 0.782 |
| Region: pay-transparency state | 1,965 | 42.7% | 85.2% | 84.6% | 0.849 |
| Region: state unknown | 1,105 | 53.8% | 83.1% | 88.4% | 0.856 |
| Hourly contract | 758 | 47.6% | 84.3% | 81.7% | 0.830 |
| Hourly full-time | 1,633 | 10.1% | 67.5% | 65.5% | 0.665 |

**Findings.**
- *Realistic performance:* the weakest region ("other US state", F1 0.782) contains 73% of
  non-disclosers, the population the model would be applied to. ~0.78 is the honest
  headline figure for that use, not 0.82.
- *Hourly contracts* perform like the overall model (F1 0.830), supporting D-004.
- *Errors cluster at the cut-off:* 39% of false positives pay $90–100k (all negatives: 9.8%);
  39% of false negatives pay $100–110k (all positives: 16.6%).
- *Confident errors reveal label noise:* e.g. a forklift operator at $113,048, a retail shoe
  salesperson at $119,600 and "Staff Services II" at $521,063, all scored below 2% by
  the model. Plausible-looking but wrong salaries pass the plausibility band (D-002).
- *Strongest features are sensible:* occupations (physician, pharmacist, veterinarian),
  seniority (director, senior, principal) and experience requirements ("10 years");
  no salary remnants (D-006).

**Decisions.**
- Report per-region performance alongside the overall figure.
- Use strong model–label disagreement as a data-quality review queue (human check, no
  automatic correction, consistent with D-003).
- Uncertain predictions near the cut-off are routed to human review (Phase 4).x