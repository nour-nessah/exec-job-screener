"""Screen ONE job posting from the command line: probability, queue and the deciding words.

Examples (run from the project root):
    python scripts/screen_posting.py --title "Vice President of Finance" \
        --description "Lead our finance team. 10 years of experience required." \
        --experience Executive
    python scripts/screen_posting.py --title "Data Analyst" --description-file posting.txt
"""
import argparse
from pathlib import Path

import joblib
import pandas as pd

from exec_screener.explain import explain

MODEL_PATH = Path("models/model.joblib")
THRESHOLDS_PATH = Path("models/thresholds.json")
REGIONS = ["other US state", "pay-transparency state", "state unknown"]
WORK_TYPES = ["FULL_TIME", "PART_TIME", "CONTRACT", "TEMPORARY", "INTERNSHIP", "VOLUNTEER", "OTHER"]
EXPERIENCE = ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive", "missing"]
TOP_N = 6

parser = argparse.ArgumentParser(description="Screen a job posting against the $100k benchmark.")
parser.add_argument("--title", required=True)
text = parser.add_mutually_exclusive_group()
text.add_argument("--description", default="")
text.add_argument("--description-file", type=Path)
parser.add_argument("--region", choices=REGIONS, default="other US state")
parser.add_argument("--work-type", choices=WORK_TYPES, default="FULL_TIME")
parser.add_argument("--experience", choices=EXPERIENCE, default="missing")
args = parser.parse_args()

description = args.description_file.read_text() if args.description_file else args.description
posting = {
    "title": args.title,
    "description": description,
    "region": args.region,
    "work_type": args.work_type,
    "experience": args.experience,
}

model = joblib.load(MODEL_PATH)
thresholds = pd.read_json(THRESHOLDS_PATH, typ="series")
result = explain(model, posting, thresholds["t_low"], thresholds["t_high"])

print(f"\n{args.title}")
print(f"Probability of a salary >= $100k: {result.probability:.1%}   ->  {result.queue.upper()}")
print(f"(auto-reject <= {thresholds['t_low']:.0%}, auto-accept >= {thresholds['t_high']:.0%}, review in between)\n")

up = result.contributions[result.contributions["contribution"] > 0].head(TOP_N)
down = result.contributions[result.contributions["contribution"] < 0].head(TOP_N)
print(f"{'pushing UP':42s} | pushing DOWN")
for i in range(max(len(up), len(down))):
    left = f"{up.iloc[i]['contribution']:+.2f}  {up.iloc[i]['source']}: {up.iloc[i]['feature']}" if i < len(up) else ""
    right = f"{down.iloc[i]['contribution']:+.2f}  {down.iloc[i]['source']}: {down.iloc[i]['feature']}" if i < len(down) else ""
    print(f"{left[:42]:42s} | {right}")