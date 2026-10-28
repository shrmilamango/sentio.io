"""Scoring shared by the baseline and the transformer models."""
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from labels import ASPECTS, ASPECT_CLASSES, OVERALL


def score(gold: pd.DataFrame, pred: pd.DataFrame) -> dict:
    """gold/pred: columns overall_sentiment + one per aspect (already mapped)."""
    out = {
        "overall_macro_f1": f1_score(gold.overall_sentiment, pred.overall_sentiment,
                                     labels=OVERALL, average="macro", zero_division=0),
        "overall_accuracy": accuracy_score(gold.overall_sentiment, pred.overall_sentiment),
        "overall_f1_per_class": dict(zip(OVERALL, f1_score(
            gold.overall_sentiment, pred.overall_sentiment, labels=OVERALL,
            average=None, zero_division=0).round(4).tolist())),
        "aspects": {},
    }
    det, sent = [], []
    for a in ASPECTS:
        g, p = gold[a], pred[a]
        d = f1_score(g != "none", p != "none", zero_division=0)
        present = [c for c in ASPECT_CLASSES if (g == c).any()]
        s = f1_score(g, p, labels=present, average="macro", zero_division=0)
        det.append(d); sent.append(s)
        out["aspects"][a] = {"detection_f1": round(d, 4), "sentiment_macro_f1": round(s, 4),
                             "support": {k: int(v) for k, v in g.value_counts().items()}}
    out["aspect_detection_f1_avg"] = float(np.mean(det))
    out["aspect_sentiment_macro_f1_avg"] = float(np.mean(sent))
    # one number for model selection on VAL
    out["selection_score"] = float(np.mean([out["overall_macro_f1"],
                                            out["aspect_detection_f1_avg"],
                                            out["aspect_sentiment_macro_f1_avg"]]))
    for k in ("overall_macro_f1", "overall_accuracy", "aspect_detection_f1_avg",
              "aspect_sentiment_macro_f1_avg", "selection_score"):
        out[k] = round(float(out[k]), 4)
    return out
