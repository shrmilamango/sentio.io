"""
Placeholder predictor.

Returns responses in exactly the same shape the real ML service will, so the
frontend can be built against it. Replace with a call to the ML service once
MuRIL is fine-tuned, then set USE_FAKE_MODEL=False in .env.

The logic here is a crude keyword lexicon. It is NOT the project's model and
is not evaluated anywhere. It exists only to make the API return plausible data.
"""

import random
import re
import time

MODEL_VERSION = "fake-lexicon-v0"

NEGATIVE_WORDS = {
    "ghatiya", "bakwas", "bakwaas", "bekar", "bekaar", "kharab", "kharaab",
    "ganda", "gandi", "thanda", "late", "der", "cancel", "fraud", "chor",
    "worst", "bad", "slow", "cold", "mehnga", "mahenga", "spill", "leak",
}
POSITIVE_WORDS = {
    "achha", "acha", "accha", "badhiya", "mast", "tasty", "fast", "good",
    "best", "great", "jaldi", "garam", "fresh", "zabardast", "sahi",
}
HINDI_MARKERS = {
    "hai", "tha", "thi", "nahi", "nhi", "bahut", "bhot", "yaar", "bhai",
    "kya", "aur", "par", "lekin", "ekdum", "bilkul", "khana", "paisa",
}

ASPECT_KEYWORDS = {
    "delivery_time":    ["late", "der", "time", "slow", "fast", "jaldi", "deliver", "ghante", "minute"],
    "food_quality":     ["khana", "food", "taste", "tasty", "thanda", "garam", "fresh", "quality", "basi"],
    "packaging":        ["packing", "packaging", "container", "leak", "spill", "gir", "tuta"],
    "delivery_partner": ["delivery boy", "rider", "partner", "bhaiya", "rude", "call"],
    "app_experience":   ["app", "crash", "login", "payment", "update", "slow app", "bug"],
    "price_offers":     ["price", "mehnga", "mahenga", "charge", "coupon", "offer", "discount", "rate"],
    "refund_support":   ["refund", "cancel", "support", "customer care", "paisa wapas", "complaint"],
}

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF]"
)


# Words that separate two opinions in one sentence.
CLAUSE_SPLIT_RE = re.compile(
    r"\s+(?:par|but|lekin|magar|however|aur|and)\s+|[,;.!?]\s*"
)


def _clause_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of each clause in the text."""
    spans, pos = [], 0
    for m in CLAUSE_SPLIT_RE.finditer(text):
        if m.start() > pos:
            spans.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    return spans or [(0, len(text))]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\w']+|" + EMOJI_RE.pattern, text)


def _classify_lang(token: str) -> str:
    if EMOJI_RE.fullmatch(token):
        return "emoji"
    if re.search(r"[ऀ-ॿ]", token):
        return "hi_deva"
    low = token.lower()
    if low in HINDI_MARKERS or low in NEGATIVE_WORDS or low in POSITIVE_WORDS:
        return "hi_roman" if low in HINDI_MARKERS else "en"
    return "en"


def predict(text: str) -> dict:
    start = time.perf_counter()
    tokens = _tokenize(text)
    lower = text.lower()

    # --- token attributions ---
    attributions = []
    score = 0.0
    for t in tokens:
        low = t.lower()
        weight = 0.0
        if low in NEGATIVE_WORDS:
            weight = -round(random.uniform(0.55, 0.85), 2)
        elif low in POSITIVE_WORDS:
            weight = round(random.uniform(0.40, 0.75), 2)
        elif EMOJI_RE.fullmatch(t):
            weight = -0.3
        score += weight
        attributions.append({"text": t, "lang": _classify_lang(t), "weight": weight})

    # --- overall polarity ---
    if score <= -0.3:
        polarity = "negative"
    elif score >= 0.3:
        polarity = "positive"
    else:
        polarity = "neutral"
    confidence = round(min(0.95, 0.55 + abs(score) * 0.12), 2)

    # --- language distribution ---
    counts: dict[str, int] = {}
    for a in attributions:
        counts[a["lang"]] = counts.get(a["lang"], 0) + 1
    total = max(1, len(attributions))
    lang_dist = {k: round(v / total, 2) for k, v in counts.items()}

    # --- aspects ---
    # Split into clauses first. "Delivery fast thi PAR packaging ghatiya"
    # holds two opposite opinions, so each clause is scored on its own.
    aspects = []
    for c_start, c_end in _clause_spans(lower):
        clause = lower[c_start:c_end]
        neg = sum(1 for w in NEGATIVE_WORDS if w in clause)
        pos = sum(1 for w in POSITIVE_WORDS if w in clause)
        if neg > pos:
            pol = "negative"
        elif pos > neg:
            pol = "positive"
        else:
            pol = "neutral"

        for key, words in ASPECT_KEYWORDS.items():
            if any(a["aspect"] == key for a in aspects):
                continue                      # first mention wins
            hit = next((w for w in words if w in clause), None)
            if not hit:
                continue
            idx = c_start + clause.find(hit)
            aspects.append({
                "aspect": key,
                "polarity": pol,
                "confidence": round(random.uniform(0.62, 0.90), 2),
                "span": [idx, min(len(text), idx + len(hit))],
            })

    normalized = re.sub(r"(.)\1{2,}", r"\1", text.lower()).strip()
    latency = int((time.perf_counter() - start) * 1000) or 1

    return {
        "normalized_text": normalized,
        "polarity": polarity,
        "confidence": confidence,
        "sarcasm": False,
        "language_distribution": lang_dist,
        "tokens": attributions,
        "aspects": aspects,
        "model_version": MODEL_VERSION,
        "latency_ms": latency,
    }
