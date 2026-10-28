"""
Build the model comparison table from results/*.json.

Output: results/comparison.csv and results/comparison.md
All scores are on the same frozen TEST split.
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
R = HERE / "results"
NAMES = {"baseline_tfidf_lr": "TF-IDF + Logistic Regression", "muril_v1": "MuRIL (float16, did not converge)",
         "muril_fp32": "MuRIL (float32, lr 5e-5, 10 epochs)",
         "mbert": "mBERT", "xlmr": "XLM-RoBERTa", "hingroberta": "HingRoBERTa - dataset v1 (Colab T4)",
         "hingroberta_v2": "HingRoBERTa (dataset v2)",
         "hingroberta_local_v1": "HingRoBERTa - dataset v1 (laptop GPU)",
         "hingroberta_local_v2": "HingRoBERTa - dataset v2 (laptop GPU)", "baseline_tfidf_lr_v2": "TF-IDF + Logistic Regression (dataset v2)"}
rows = []

for k, b in enumerate(sorted(R.glob("baseline_tfidf_lr*.json"))):
    j = json.loads(b.read_text(encoding="utf-8"))
    if k == 0:
        rows.append({"model": "Always 'negative' (majority class)",
                     "overall_macro_f1": j["overall_majority_class"]["test_macro_f1"],
                     "overall_accuracy": j["overall_majority_class"]["test_accuracy"],
                     "positive_f1": 0.0, "aspect_detection_f1": None, "aspect_sentiment_f1": None})
    rows.append({"model": NAMES.get(b.stem, b.stem),
                 "overall_macro_f1": j["overall"]["test_macro_f1"],
                 "overall_accuracy": j["overall"]["test_accuracy"],
                 "positive_f1": j["overall"]["test_f1_per_class"]["positive"],
                 "aspect_detection_f1": j["aspect_detection_f1_avg"],
                 "aspect_sentiment_f1": j["aspect_sentiment_macro_f1_avg"]})

for f in sorted(R.glob("*.json")):
    if f.stem.startswith("baseline_tfidf_lr") or f.stem == "comparison":
        continue
    j = json.loads(f.read_text(encoding="utf-8"))
    if "test" not in j:
        continue
    t = j["test"]
    rows.append({"model": NAMES.get(f.stem, f.stem),
                 "overall_macro_f1": t["overall_macro_f1"], "overall_accuracy": t["overall_accuracy"],
                 "positive_f1": t["overall_f1_per_class"]["positive"],
                 "aspect_detection_f1": t["aspect_detection_f1_avg"],
                 "aspect_sentiment_f1": t["aspect_sentiment_macro_f1_avg"]})

df = pd.DataFrame(rows)
df.to_csv(R / "comparison.csv", index=False)
md = ["| Model | Overall macro-F1 | Accuracy | Positive F1 | Aspect detection F1 | Aspect sentiment F1 |",
      "|---|---|---|---|---|---|"]
fmt = lambda v: "–" if v is None or pd.isna(v) else f"{v:.3f}"
for r in rows:
    md.append(f"| {r['model']} | {fmt(r['overall_macro_f1'])} | {fmt(r['overall_accuracy'])} | "
              f"{fmt(r['positive_f1'])} | {fmt(r['aspect_detection_f1'])} | {fmt(r['aspect_sentiment_f1'])} |")
(R / "comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
