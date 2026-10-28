"""Shared label definitions used by every training script."""

OVERALL = ["negative", "neutral", "positive"]

ASPECTS = ["delivery_time", "food_quality", "packaging", "delivery_partner",
           "app_experience", "price_offers", "refund_support"]

# Aspect heads predict 3 classes. 'neutral' aspect labels are very rare
# (29 of ~2,500 aspect mentions), so they are merged into 'positive',
# i.e. "mentioned, not a complaint". Documented as a design decision.
ASPECT_CLASSES = ["none", "negative", "positive"]


def aspect_label(value: str) -> str:
    value = value.strip().lower()
    return "positive" if value == "neutral" else value
