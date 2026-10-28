"""
compute_kappa.py
Inter-annotator agreement for the Sentio.io annotation round.

Reads the overlap sheet where all three annotators labelled the same reviews
independently, computes Cohen's kappa for every annotator pair, and lists the
reviews they disagreed on.

Usage:
    python compute_kappa.py
    python compute_kappa.py --file annotation/kappa_round.csv

Output:
    printed report + annotation/kappa_report.txt
"""

import argparse
import os
from itertools import combinations

import pandas as pd
from sklearn.metrics import cohen_kappa_score

ANNOTATORS = ["A", "B", "C"]
COLUMN = "overall"          # change to an aspect name to measure that instead
VALID = {"positive", "negative", "neutral"}


def interpret(k):
    if k < 0.20:  return "poor"
    if k < 0.40:  return "fair"
    if k < 0.60:  return "moderate"
    if k < 0.80:  return "substantial"
    return "almost perfect"


def main(path, out_dir):
    df = pd.read_csv(path, dtype=str).fillna("")

    cols = [f"{COLUMN}_{a}" for a in ANNOTATORS]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing columns in {path}: {missing}")

    for c in cols:
        df[c] = df[c].str.strip().str.lower()

    lines = []
    def out(s=""):
        print(s)
        lines.append(s)

    # ---- completeness ----
    incomplete = df[(df[cols] == "").any(axis=1)]
    if len(incomplete):
        out(f"WARNING: {len(incomplete)} rows are not labelled by all three annotators.")
        for _, r in incomplete.iterrows():
            who = [a for a in ANNOTATORS if r[f"{COLUMN}_{a}"] == ""]
            out(f"   {r['id']}  missing: {', '.join(who)}")
        out()

    bad = set()
    for c in cols:
        bad |= set(df[c].unique()) - VALID - {""}
    if bad:
        out(f"WARNING: unexpected label values found: {sorted(bad)}")
        out()

    sub = df[(df[cols] != "").all(axis=1)]

    # ---- kappa ----
    out("COHEN'S KAPPA \u2014 INTER-ANNOTATOR AGREEMENT")
    out("=" * 58)
    out(f"Field evaluated       : {COLUMN}")
    out(f"Reviews in overlap    : {len(df)}")
    out(f"Fully labelled        : {len(sub)}")
    out()

    scores = []
    for x, y in combinations(ANNOTATORS, 2):
        k = cohen_kappa_score(sub[f"{COLUMN}_{x}"].tolist(),
                              sub[f"{COLUMN}_{y}"].tolist())
        scores.append(k)
        out(f"  {x} \u2013 {y}   {k:.3f}   ({interpret(k)})")

    mean_k = sum(scores) / len(scores)
    out("  " + "-" * 34)
    out(f"  mean    {mean_k:.3f}   ({interpret(mean_k)})")
    out()

    # ---- label distribution ----
    out("LABEL DISTRIBUTION")
    out("-" * 58)
    out(f"{'label':<12}" + "".join(f"{a:>10}" for a in ANNOTATORS))
    for label in ["positive", "negative", "neutral"]:
        row = "".join(f"{(sub[f'{COLUMN}_{a}'] == label).sum():>10}" for a in ANNOTATORS)
        out(f"{label:<12}{row}")
    out()

    # ---- disagreements ----
    def differs(r):
        return len({r[f"{COLUMN}_{a}"] for a in ANNOTATORS}) > 1

    dis = sub[sub.apply(differs, axis=1)]
    out("DISAGREEMENTS")
    out("-" * 58)
    out(f"{len(dis)} of {len(sub)} reviews ({len(dis)/len(sub):.0%})")
    out()
    for _, r in dis.iterrows():
        labels = "  ".join(f"{a}={r[f'{COLUMN}_{a}']:<9}" for a in ANNOTATORS)
        out(f"{r['id']}  {labels}")
        out(f"        {r['review_text'][:88]}")
    out()
    out("Resolve each case together, record the decision as a rule in the")
    out("annotation guidelines, then relabel and re-run this script.")

    os.makedirs(out_dir, exist_ok=True)
    report = os.path.join(out_dir, "kappa_report.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nSaved {report}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", default="annotation/kappa_round.csv")
    p.add_argument("--out",  default="annotation")
    a = p.parse_args()
    main(a.file, a.out)