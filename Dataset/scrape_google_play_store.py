"""
STEP 1 — SCRAPE
Collects raw reviews from Play Store for food delivery apps.

Install first:
    pip install google-play-scraper pandas

Run:
    python 1_scrape.py

Output: raw/raw_reviews_playstore.csv  (~20,000 rows)
Time: 15-25 minutes
"""

import pandas as pd
from google_play_scraper import Sort, reviews

# App package IDs — find these in the Play Store URL
# https://play.google.com/store/apps/details?id=in.swiggy.android
APPS = {
    "swiggy":      "in.swiggy.android",
    "zomato":      "com.application.zomato",
    "zepto":       "com.zeptoconsumerapp",
    "blinkit":     "com.grofers.customerapp",
    "dominos":     "com.Dominos",
    "eatsure":     "com.done.faasos",
    "magicpin":    "com.magicpin.local",
    "instamart":   "in.swiggy.android",
    "mcdonalds":   "com.mcdonalds.mobileapp",
    "kfc":         "com.yum.kfc",
    "burgerking":  "in.burgerking.android",
    "wowmomo":     "com.wowmomo.woweats",
    "bigbasket":   "com.bigbasket.mobileapp",
}

# Pull more 1-2 star reviews: complaints contain aspects, praise usually doesn't
TARGETS = [
    (1, 3000),
    (2, 2500),
    (3, 1500),
    (4, 1000),
    (5, 1000),
]

all_rows = []

for app_name, package in APPS.items():
    print(f"\n=== {app_name} ===")
    for stars, count in TARGETS:
        try:
            result, _ = reviews(
                package,
                lang="en",          # 'en' returns Roman-script reviews (what we want)
                country="in",
                sort=Sort.NEWEST,
                count=count,
                filter_score_with=stars,
            )
            for r in result:
                all_rows.append({
                    "review_id":   r["reviewId"],
                    "review_text": (r["content"] or "").replace("\n", " ").strip(),
                    "star_rating": r["score"],
                    "date":        r["at"].strftime("%Y-%m-%d") if r["at"] else "",
                    "app_name":    app_name,
                    "thumbs_up":   r["thumbsUpCount"],
                })
            print(f"  {stars}* -> {len(result)} reviews")
        except Exception as e:
            print(f"  {stars}* FAILED: {e}")

df = pd.DataFrame(all_rows)
df = df.drop_duplicates(subset=["review_id"])
df = df[df["review_text"].str.len() > 0]
df.to_csv("raw/raw_reviews_playstore.csv", index=False)

print(f"\nSaved raw_reviews_playstore.csv  —  {len(df)} rows")
print(df["app_name"].value_counts())
print(df["star_rating"].value_counts().sort_index())