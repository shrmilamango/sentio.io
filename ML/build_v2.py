"""
Build dataset v2 = v1 + the newly annotated 4/5-star reviews.

- UNSURE / EXCLUDE rows are kept out (listed in Dataset/annotation/excluded_v2.csv).
- The TEST split is frozen: v2 test = v1 test, row for row, so v1 and v2
  models are compared on exactly the same reviews.
- New reviews go to train (85%) / val (15%), stratified on overall sentiment.

Run:  python build_v2.py
"""
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

SEED = 42
ROOT = Path(__file__).resolve().parent.parent
D, ML = ROOT / "Dataset", ROOT / "ML"
LABELS = ["overall_sentiment", "delivery_time", "food_quality", "packaging", "delivery_partner",
          "app_experience", "price_offers", "refund_support", "sarcasm"]

v1 = pd.read_csv(D / "sentio_dataset_v1.csv", dtype=str, keep_default_na=False)
new = pd.read_csv(D / "annotation" / "annotated_v2.csv", dtype=str, keep_default_na=False)
for c in new.columns:
    if c != "review_text":
        new[c] = new[c].str.strip()
for c in LABELS:
    new[c] = new[c].str.lower()

skip = new.notes.str.upper().isin(["UNSURE", "EXCLUDE"])
new[skip][["id", "review_text", "app_name", "source", "star_rating", "annotator", "notes"]] \
    .rename(columns={"notes": "reason"}).to_csv(D / "annotation" / "excluded_v2.csv", index=False, encoding="utf-8")
new = new[~skip].drop(columns=["notes"])
assert (new[LABELS] != "").all().all(), "blank labels in new rows"
assert list(new.columns) == list(v1.columns)

v2 = pd.concat([v1, new], ignore_index=True)
assert v2.id.is_unique
v2.to_csv(D / "sentio_dataset_v2.csv", index=False, encoding="utf-8")

S1, S2 = ML / "splits_v1", ML / "splits_v2"
S2.mkdir(exist_ok=True)
tr1, va1, te1 = (pd.read_csv(S1 / f"{n}.csv", dtype=str, keep_default_na=False) for n in ("train", "val", "test"))
ntr, nva = train_test_split(new, test_size=0.15, stratify=new.overall_sentiment, random_state=SEED)
tr2 = pd.concat([tr1, ntr]).sort_values("id")
va2 = pd.concat([va1, nva]).sort_values("id")
te2 = te1                                   # frozen
for name, part in (("train", tr2), ("val", va2), ("test", te2)):
    part.to_csv(S2 / f"{name}.csv", index=False, encoding="utf-8")

lines = [f"v2 = v1 ({len(v1)}) + new ({len(new)}) = {len(v2)} rows;  {skip.sum()} new rows excluded (UNSURE)",
         "TEST split frozen = identical to splits_v1/test.csv", "",
         f"{'split':<6}{'rows':>6}{'neg':>6}{'neu':>6}{'pos':>6}"]
for name, part in (("train", tr2), ("val", va2), ("test", te2)):
    vc = part.overall_sentiment.value_counts()
    lines.append(f"{name:<6}{len(part):>6}{vc.get('negative',0):>6}{vc.get('neutral',0):>6}{vc.get('positive',0):>6}")
lines += ["", "Positive aspect labels in TRAIN (v1 -> v2):"]
for a in LABELS[1:8]:
    lines.append(f"  {a:<17}{(tr1[a].isin(['positive','neutral'])).sum():>5} -> {(tr2[a].isin(['positive','neutral'])).sum():>4}")
report = "\n".join(lines)
(S2 / "split_report.txt").write_text(report, encoding="utf-8")
print(report)
