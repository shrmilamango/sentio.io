"""
Baseline: TF-IDF (word + character n-grams) + Logistic Regression.

One classifier for overall sentiment, one per aspect. Class weights are
balanced so rare labels (positive) are not ignored.

C is chosen on the VAL split only. TEST is scored once at the end.

Run:  python baseline.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

from labels import ASPECTS, ASPECT_CLASSES, OVERALL, aspect_label

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--splits", default="splits_v1")
ap.add_argument("--out", default="baseline_tfidf_lr")
args = ap.parse_args()

HERE = Path(__file__).resolve().parent
SPLITS = HERE / args.splits
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)

train = pd.read_csv(SPLITS / "train.csv", dtype=str, keep_default_na=False)
val = pd.read_csv(SPLITS / "val.csv", dtype=str, keep_default_na=False)
test = pd.read_csv(SPLITS / "test.csv", dtype=str, keep_default_na=False)

word = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, sublinear_tf=True)
char = TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
Xtr = hstack([word.fit_transform(train.review_text), char.fit_transform(train.review_text)]).tocsr()
Xva = hstack([word.transform(val.review_text), char.transform(val.review_text)]).tocsr()
Xte = hstack([word.transform(test.review_text), char.transform(test.review_text)]).tocsr()


def fit_best(y_tr, y_va, labels):
    best = None
    for C in [0.25, 1, 4, 16]:
        clf = LogisticRegression(C=C, class_weight="balanced", max_iter=3000)
        clf.fit(Xtr, y_tr)
        f = f1_score(y_va, clf.predict(Xva), labels=labels, average="macro", zero_division=0)
        if best is None or f > best[0]:
            best = (f, C, clf)
    return best


results = {}

# ---- overall ----
f_val, C, clf = fit_best(train.overall_sentiment, val.overall_sentiment, OVERALL)
pred = clf.predict(Xte)
results["overall"] = {
    "C": C,
    "val_macro_f1": round(f_val, 4),
    "test_macro_f1": round(f1_score(test.overall_sentiment, pred, labels=OVERALL, average="macro", zero_division=0), 4),
    "test_accuracy": round(accuracy_score(test.overall_sentiment, pred), 4),
    "test_f1_per_class": dict(zip(OVERALL, np.round(f1_score(test.overall_sentiment, pred, labels=OVERALL, average=None, zero_division=0), 4).tolist())),
}
majority = ["negative"] * len(test)
results["overall_majority_class"] = {
    "test_macro_f1": round(f1_score(test.overall_sentiment, majority, labels=OVERALL, average="macro", zero_division=0), 4),
    "test_accuracy": round(accuracy_score(test.overall_sentiment, majority), 4),
}

# ---- aspects ----
det, sent = [], []
results["aspects"] = {}
for a in ASPECTS:
    ytr, yva, yte = (d[a].map(aspect_label) for d in (train, val, test))
    f_val, C, clf = fit_best(ytr, yva, ASPECT_CLASSES)
    p = pd.Series(clf.predict(Xte), index=yte.index)
    detection = f1_score(yte != "none", p != "none", zero_division=0)
    # macro-F1 over the classes that actually occur in the test gold labels
    present = [c for c in ASPECT_CLASSES if (yte == c).any()]
    sentiment = f1_score(yte, p, labels=present, average="macro", zero_division=0)
    det.append(detection); sent.append(sentiment)
    results["aspects"][a] = {
        "C": C,
        "test_detection_f1": round(detection, 4),
        "test_sentiment_macro_f1": round(sentiment, 4),
        "test_support": {k: int(v) for k, v in yte.value_counts().items()},
    }
results["aspect_detection_f1_avg"] = round(float(np.mean(det)), 4)
results["aspect_sentiment_macro_f1_avg"] = round(float(np.mean(sent)), 4)

(OUT / f"{args.out}.json").write_text(json.dumps(results, indent=2, default=int), encoding="utf-8")

print(f"Overall sentiment   macro-F1 {results['overall']['test_macro_f1']:.3f}   "
      f"acc {results['overall']['test_accuracy']:.3f}   per class {results['overall']['test_f1_per_class']}")
print(f"Majority class      macro-F1 {results['overall_majority_class']['test_macro_f1']:.3f}   "
      f"acc {results['overall_majority_class']['test_accuracy']:.3f}")
print(f"Aspect detection    avg F1   {results['aspect_detection_f1_avg']:.3f}")
print(f"Aspect sentiment    avg macro-F1 {results['aspect_sentiment_macro_f1_avg']:.3f}")
for a, r in results["aspects"].items():
    print(f"   {a:<17} detect {r['test_detection_f1']:.3f}   sentiment {r['test_sentiment_macro_f1']:.3f}   {r['test_support']}")
