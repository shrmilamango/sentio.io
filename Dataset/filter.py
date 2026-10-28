"""
2_filter.py  —  merges Play Store + Google Maps, filters to code-mixed, builds the sheet.

Input : raw/raw_reviews_playstore.csv
        raw/dataset_Google-Maps-*.csv   (any number, optional)
        hindi_words.txt
Output: annotation/to_annotate.csv      ready to upload to Google Sheets
        filter_report.txt    the funnel, for your methodology section
"""

import re, glob
import pandas as pd

TARGET     = 2000
MIN_HINDI  = 0.20
MIN_WORDS  = 6
MAX_WORDS  = 60

HINDI = set(w.strip().lower() for w in open("hindi_words.txt") if w.strip())

PII = [re.compile(p) for p in [
    r"\b\d{10}\b",
    r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    r"[\w\.-]+@[\w\.-]+\.\w+",
    r"\bhttps?://\S+",
]]

def words(t):      return re.findall(r"[a-zA-Z]+", str(t).lower())
def n_words(t):    return len(words(t))
def has_pii(t):    return any(p.search(str(t)) for p in PII)
def dedup_key(t):  return re.sub(r"[^a-z0-9]+", "", str(t).lower())

def hindi_ratio(t):
    w = words(t)
    return sum(1 for x in w if x in HINDI) / len(w) if w else 0.0

log = []
def step(name, df):
    line = f"{name:<40} {len(df):>7}"
    log.append(line)
    print(line)
    return df

# ---------------- load ----------------
frames = []

try:
    ps = pd.read_csv("raw/raw_reviews_playstore.csv", low_memory=False)
    ps = ps[["review_text", "star_rating", "date", "app_name"]].copy()
    ps["source"] = "playstore"
    frames.append(ps)
    print(f"  play store              {len(ps):>7}")
except FileNotFoundError:
    print("  play store              (not found)")

for f in sorted(glob.glob("raw/dataset_Google-Maps*.csv")):
    d = pd.read_csv(f, low_memory=False)
    frames.append(pd.DataFrame({
        "review_text": d["text"],
        "star_rating": d["stars"],
        "date":        d["publishedAtDate"] if "publishedAtDate" in d else "",
        "app_name":    "gmaps",
        "source":      "gmaps",
    }))
    print(f"  {f[-18:]:<24}{len(d):>7}")

if not frames:
    raise SystemExit("No input files found.")

df = pd.concat(frames, ignore_index=True)
step("0. merged", df)

# ---------------- filter ----------------
df["review_text"] = (df["review_text"].astype(str)
                     .str.replace(r"\s+", " ", regex=True).str.strip())
df = df[(df.review_text.str.len() > 0) & (df.review_text != "nan")]
step("1. non-empty", df)

df = df[~df.review_text.apply(has_pii)]
step("2. PII removed", df)

df["n_words"] = df.review_text.apply(n_words)
df = df[(df.n_words >= MIN_WORDS) & (df.n_words <= MAX_WORDS)]
step(f"3. {MIN_WORDS}-{MAX_WORDS} words", df)

df["_k"] = df.review_text.apply(dedup_key)
df = df.drop_duplicates(subset="_k")
step("4. deduplicated", df)

df["hindi_ratio"] = df.review_text.apply(hindi_ratio)
df = df[df.hindi_ratio >= MIN_HINDI]
step(f"5. code-mixed (>={MIN_HINDI:.0%} Hindi)", df)

# ---------------- balance ----------------
# Code-mixed reviews are scarce, so keep them all rather than forcing equal
# star buckets. We only cap any single app from dominating the set.
gmaps = df[df.source == "gmaps"]
ps    = df[df.source == "playstore"]

MAX_PER_APP = max(120, int(TARGET * 0.18))
kept = []
for a in sorted(ps.app_name.unique()):
    pool = ps[ps.app_name == a]
    if len(pool) > MAX_PER_APP:
        pool = pool.sample(MAX_PER_APP, random_state=42)
    kept.append(pool)

out = pd.concat([gmaps] + kept)
if len(out) > TARGET:
    out = out.sample(TARGET, random_state=42)
out = out.sample(frac=1, random_state=42).reset_index(drop=True)
step("6. capped per app", out)

# ---------------- build the sheet ----------------
ASPECTS = ["delivery_time", "food_quality", "packaging", "delivery_partner",
           "app_experience", "price_offers", "refund_support"]

out.insert(0, "id", [f"FD{i:04d}" for i in range(1, len(out) + 1)])

sheet = out[["id", "review_text", "app_name", "source", "star_rating"]].copy()
sheet["overall_sentiment"] = ""
for a in ASPECTS:
    sheet[a] = ""
sheet["sarcasm"]   = ""
sheet["annotator"] = ""
sheet["notes"]     = ""
sheet.to_csv("annotation/to_annotate.csv", index=False)

with open("annotation/filter_report_v1.txt", "w") as f:
    f.write("COLLECTION FUNNEL\n" + "=" * 50 + "\n")
    f.write("\n".join(log))
    f.write(f"\n\nFinal: {len(sheet)} reviews\n")
    f.write("\nBy source:\n"  + out.source.value_counts().to_string())
    f.write("\n\nBy app:\n"   + out.app_name.value_counts().to_string())
    f.write("\n\nBy star:\n"  + out.star_rating.value_counts().sort_index().to_string())
    f.write(f"\n\nMean Hindi ratio: {out.hindi_ratio.mean():.2f}\n")
    f.write(f"Mean length: {out.n_words.mean():.1f} words\n")

print(f"\nWrote to_annotate.csv ({len(sheet)} rows) and filter_report.txt")