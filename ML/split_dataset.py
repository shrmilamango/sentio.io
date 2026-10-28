"""
Split sentio_dataset_v1.csv into train / val / test (70 / 15 / 15).

- Stratified on overall_sentiment so every split has the same
  negative / neutral / positive mix.
- Fixed seed, so the split is identical every time it is run.
- The TEST split is frozen: never train or tune on it. It is used once,
  at the very end, to report the final numbers.

Run:  python split_dataset.py
"""
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

SEED = 42
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Dataset" / "sentio_dataset_v1.csv"
OUT = ROOT / "ML" / "splits_v1"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SRC, dtype=str, keep_default_na=False)

train, rest = train_test_split(df, test_size=0.30, stratify=df.overall_sentiment, random_state=SEED)
val, test = train_test_split(rest, test_size=0.50, stratify=rest.overall_sentiment, random_state=SEED)

for name, part in [("train", train), ("val", val), ("test", test)]:
    part.sort_values("id").to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8")

ASPECTS = ["delivery_time", "food_quality", "packaging", "delivery_partner",
           "app_experience", "price_offers", "refund_support"]
lines = [f"Source: {SRC.name}  ({len(df)} rows)   seed={SEED}", ""]
lines.append(f"{'split':<6}{'rows':>6}{'neg':>6}{'neu':>6}{'pos':>6}")
for name, part in [("train", train), ("val", val), ("test", test)]:
    vc = part.overall_sentiment.value_counts()
    lines.append(f"{name:<6}{len(part):>6}{vc.get('negative',0):>6}{vc.get('neutral',0):>6}{vc.get('positive',0):>6}")
lines += ["", "Aspect mentions (non-'none') per split:"]
lines.append(f"{'aspect':<18}{'train':>7}{'val':>6}{'test':>6}")
for a in ASPECTS:
    lines.append(f"{a:<18}" + "".join(f"{(p[a]!='none').sum():>{w}}" for p, w in [(train,7),(val,6),(test,6)]))
report = "\n".join(lines)
(OUT / "split_report.txt").write_text(report, encoding="utf-8")
print(report)
