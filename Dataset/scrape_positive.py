"""
Collect MORE positive (and some neutral) code-mixed reviews.

Why: sentio_dataset_v1 has only 136 positive reviews out of 1,844, so the
model cannot learn what praise looks like. This pulls 3/4/5-star Play Store
reviews and applies EXACTLY the same filter as filter.py:

    PII removed -> 6 to 60 words -> deduplicated -> Hindi ratio >= 0.20

It also drops anything already in raw_reviews_playstore.csv or the v1
dataset, so nothing is annotated twice.

Output:
    raw_reviews_playstore_v2.csv   everything scraped (for the record)
    to_annotate_v2.csv             new reviews, IDs from FD1858, labels blank
    filter_report_v2.txt           the funnel, for the methodology section
Log:
    ../ML/logs/scrape_v2.log
"""
import re
from pathlib import Path

import pandas as pd
from google_play_scraper import Sort, reviews

HERE = Path(__file__).resolve().parent
LOG = HERE.parent / "ML" / "logs" / "scrape_v2.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
LOG.write_text("", encoding="utf-8")


def log(msg: str) -> None:
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


APPS = {
    "swiggy": "in.swiggy.android",
    "zomato": "com.application.zomato",
    "zepto": "com.zeptoconsumerapp",
    "blinkit": "com.grofers.customerapp",
    "dominos": "com.Dominos",
    "eatsure": "com.done.faasos",
    "magicpin": "com.magicpin.local",
    "mcdonalds": "com.mcdonalds.mobileapp",
    "kfc": "com.yum.kfc",
    "burgerking": "in.burgerking.android",
    "wowmomo": "com.wowmomo.woweats",
    "bigbasket": "com.bigbasket.mobileapp",
}
# (stars, how many to request per app). Code-mixed yield is ~1% for
# 4-5 star reviews, so we need a large pool.
TARGETS = [(5, 6000), (4, 6000), (3, 2000)]

MAX_NEW = 450          # cap on reviews sent for annotation
MAX_PER_APP = 60       # keep apps balanced
MIN_HINDI, MIN_WORDS, MAX_WORDS = 0.20, 6, 60

HINDI = set(w.strip().lower() for w in open(HERE / "hindi_words.txt", encoding="utf-8") if w.strip())
PII = [re.compile(p) for p in [
    r"\b\d{10}\b", r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    r"[\w\.-]+@[\w\.-]+\.\w+", r"\bhttps?://\S+",
]]


def words(t): return re.findall(r"[a-zA-Z]+", str(t).lower())
def has_pii(t): return any(p.search(str(t)) for p in PII)
def dedup_key(t): return re.sub(r"[^a-z0-9]+", "", str(t).lower())
def hindi_ratio(t):
    w = words(t)
    return sum(1 for x in w if x in HINDI) / len(w) if w else 0.0


# ---------------- scrape ----------------
rows = []
for app, package in APPS.items():
    for stars, count in TARGETS:
        try:
            result, _ = reviews(package, lang="en", country="in", sort=Sort.NEWEST,
                                count=count, filter_score_with=stars)
            for r in result:
                rows.append({
                    "review_id": r["reviewId"],
                    "review_text": (r["content"] or "").replace("\n", " ").strip(),
                    "star_rating": r["score"],
                    "date": r["at"].strftime("%Y-%m-%d") if r["at"] else "",
                    "app_name": app,
                    "thumbs_up": r["thumbsUpCount"],
                })
            log(f"{app:<11} {stars}* -> {len(result)}")
        except Exception as e:
            log(f"{app:<11} {stars}* FAILED: {e}")

raw = pd.DataFrame(rows).drop_duplicates("review_id")
raw.to_csv(HERE / "raw" / "raw_reviews_playstore_v2.csv", index=False, encoding="utf-8")

# ---------------- filter (same rules as filter.py) ----------------
funnel = []
def step(name, df):
    funnel.append(f"{name:<45} {len(df):>7}")
    log(funnel[-1])
    return df

df = step("0. scraped (3-5 star)", raw.copy())
df["review_text"] = df.review_text.astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
df = step("1. non-empty", df[df.review_text.str.len() > 0])
df = step("2. PII removed", df[~df.review_text.apply(has_pii)])
n = df.review_text.apply(lambda t: len(words(t)))
df = step(f"3. {MIN_WORDS}-{MAX_WORDS} words", df[(n >= MIN_WORDS) & (n <= MAX_WORDS)])
df["key"] = df.review_text.apply(dedup_key)
df = step("4. deduplicated", df.drop_duplicates("key"))

seen = set()
old_raw = HERE / "raw" / "raw_reviews_playstore.csv"
if old_raw.exists():
    seen |= set(pd.read_csv(old_raw, usecols=["review_text"], dtype=str).review_text.map(dedup_key))
v1 = HERE / "sentio_dataset_v1.csv"
seen |= set(pd.read_csv(v1, usecols=["review_text"], dtype=str).review_text.map(dedup_key))
seen |= set(pd.read_csv(HERE / "annotation" / "excluded_v1.csv", usecols=["review_text"], dtype=str).review_text.map(dedup_key))
df = step("5. not already collected", df[~df.key.isin(seen)])

df["hindi_ratio"] = df.review_text.apply(hindi_ratio)
df = step(f"6. code-mixed (Hindi ratio >= {MIN_HINDI})", df[df.hindi_ratio >= MIN_HINDI])

# prefer 4-5 star (positives are what we lack), balance across apps
df["star_rating"] = pd.to_numeric(df.star_rating, errors="coerce")
df = df.sort_values(["star_rating", "hindi_ratio"], ascending=[False, False])
df = df.groupby("app_name", group_keys=False).head(MAX_PER_APP).head(MAX_NEW)
df = step("7. capped for annotation", df)

# ---------------- write annotation sheet ----------------
cols = ["id", "review_text", "app_name", "source", "star_rating", "overall_sentiment",
        "delivery_time", "food_quality", "packaging", "delivery_partner", "app_experience",
        "price_offers", "refund_support", "sarcasm", "annotator", "notes"]
out = pd.DataFrame({c: "" for c in cols}, index=range(len(df)))
out["id"] = [f"FD{1858 + i:04d}" for i in range(len(df))]
out["review_text"] = df.review_text.values
out["app_name"] = df.app_name.values
out["source"] = "playstore"
out["star_rating"] = df.star_rating.astype(int).values
out.to_csv(HERE / "annotation" / "to_annotate_v2.csv", index=False, encoding="utf-8")

stars = out.star_rating.value_counts().sort_index().to_dict()
report = "\n".join(funnel + ["", f"Stars in to_annotate_v2.csv: {stars}",
                             f"Apps: {out.app_name.value_counts().to_dict()}"])
(HERE / "annotation" / "filter_report_v2.txt").write_text(report, encoding="utf-8")
log("")
log(f"Stars: {stars}")
log(f"SCRAPE DONE - {len(out)} reviews written to to_annotate_v2.csv")
