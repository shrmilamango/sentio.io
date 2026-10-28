"""
Seed the database with sample analyses so the dashboard is never empty.

Run after the API has started once (so tables exist):
    python seed.py
"""

from fastapi.testclient import TestClient

from app.main import app

SAMPLES = [
    "Delivery fast thi par packaging ekdum ghatiya",
    "Khana bahut tasty tha aur jaldi aa gaya",
    "Refund ke liye 10 din se wait kar raha hu koi response nahi",
    "App crash ho raha hai payment karte time bahut bekar",
    "Delivery boy rude tha lekin khana achha tha",
    "Order 1 ghante late aaya aur khana thanda tha",
    "Bahut mehnga ho gaya hai aaj kal, rate badha diye",
    "Packing acchi thi kuch leak nahi hua",
    "Coupon apply nahi ho raha tha app me",
    "Biryani mast thi, delivery bhi on time",
    "Container tuta hua tha sara dal gir gaya",
    "Customer care wale sirf sorry bolte hai solution nahi",
]

with TestClient(app) as client:
    for text in SAMPLES:
        r = client.post("/v1/analyze", json={"text": text, "source_app": "swiggy"})
        d = r.json()
        print(f"{d['polarity']:<9} {text[:55]}")

    print(f"\nSeeded {len(SAMPLES)} reviews.")
