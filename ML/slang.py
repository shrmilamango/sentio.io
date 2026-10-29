"""
Slang guard: a small safety net on top of the model.

The training data comes mostly from the Play Store, which hides abusive words,
so the model has never seen slang like "tatti" or "kachra". On a review such as
"tatti tha khana" it only reads "khana" and guesses positive.

This rule corrects that one failure: when a review contains a strongly negative
slang word, is not negated ("bekar nahi tha"), has no "but"-style contrast, and
the model still says positive, the overall verdict and any positive aspects are
switched to negative. Everything else is left to the model.

The proper fix is to add such reviews to the dataset and retrain.
"""
import re

# Strongly negative Hinglish / English words. Spelling variants included.
NEGATIVE_SLANG = {
    "tatti", "tatty", "tattii", "kachra", "kachara", "bakwas", "bakwaas", "bakvas", "bekwas",
    "ghatiya", "ghatia", "ghtiya", "bekar", "bekaar", "bakar", "faltu", "faaltu",
    "ganda", "gandi", "gande", "gandagi", "sadela", "sadeli",
    "kharab", "kharaab", "khrab", "bura", "buri",
    "worst", "pathetic", "disgusting", "horrible", "terrible", "awful", "trash", "garbage",
    "useless", "yuck", "rubbish",
}
NEGATIONS = {"nahi", "nhi", "nahin", "na", "not", "no", "never", "mat"}
CONTRAST = {"par", "pr", "but", "lekin", "magar", "however", "although", "though", "kintu"}

_WORD = re.compile(r"[a-z']+")


def find_slang(text: str) -> list[str]:
    """Strong negative slang words in the text that are not negated nearby."""
    words = _WORD.findall(text.lower())
    found = []
    for i, w in enumerate(words):
        if w in NEGATIONS or w not in NEGATIVE_SLANG:
            continue
        near = words[max(0, i - 2): i] + words[i + 1: i + 3]   # "bekar nahi tha", "not worst"
        if any(n in NEGATIONS for n in near):
            continue
        found.append(w)
    return found


def apply_slang_guard(text: str, polarity: str, confidence: float, aspects: list[dict]):
    """Return (polarity, confidence, aspects, applied)."""
    if polarity == "negative":
        return polarity, confidence, aspects, False
    words = set(_WORD.findall(text.lower()))
    if words & CONTRAST:          # mixed review: leave it to the model
        return polarity, confidence, aspects, False
    slang = find_slang(text)
    if not slang:
        return polarity, confidence, aspects, False
    fixed = [{**a, "polarity": "negative"} if a["polarity"] == "positive" else a for a in aspects]
    # confidence reported for a rule-based decision: fixed, moderate
    return "negative", 0.8, fixed, True
