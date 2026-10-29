from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Polarity = Literal["positive", "negative", "neutral"]


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_app: str | None = Field(None, max_length=50)

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("review text is empty")
        return v


class TokenAttribution(BaseModel):
    text: str
    lang: Literal["en", "hi_roman", "hi_deva", "emoji", "other"]
    weight: float          # -1.0 .. 1.0, negative pulls toward negative


class AspectVerdict(BaseModel):
    aspect: str
    polarity: Polarity
    confidence: float
    span: list[int] | None = None   # [start, end] in the raw text


class ModelOutput(BaseModel):
    """What the model service (or the placeholder) must return. Checked before saving."""
    normalized_text: str
    polarity: Polarity
    confidence: float = Field(..., ge=0, le=1)
    sarcasm: bool
    language_distribution: dict[str, float]
    tokens: list[TokenAttribution]
    aspects: list[AspectVerdict]
    model_version: str = Field(..., max_length=100)
    latency_ms: int


class AnalyzeResponse(BaseModel):
    id: int
    text: str
    normalized_text: str
    polarity: Polarity
    confidence: float
    sarcasm: bool
    language_distribution: dict[str, float]
    tokens: list[TokenAttribution]
    aspects: list[AspectVerdict]
    model_version: str
    latency_ms: int


class ReviewSummary(BaseModel):
    id: int
    text: str
    polarity: Polarity
    confidence: float
    created_at: datetime


class ReviewPage(BaseModel):
    items: list[ReviewSummary]
    page: int
    page_size: int
    total: int


class AspectBreakdown(BaseModel):
    aspect: str
    positive: int
    negative: int
    neutral: int


class InsightsSummary(BaseModel):
    total_reviews: int
    polarity_counts: dict[str, int]
    aspect_breakdown: list[AspectBreakdown]
    language_split: dict[str, float]


class FeedbackRequest(BaseModel):
    is_correct: bool
    correct_polarity: Polarity | None = None
    note: str | None = Field(None, max_length=500)


class FeedbackOut(BaseModel):
    analysis_id: int
    is_correct: bool
    correct_polarity: Polarity | None


class ModelInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_model: str | None
    train_size: int | None
    macro_f1: float | None
    is_active: bool
    trained_at: datetime


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str | None = Field(None, max_length=100)

    @field_validator("username")
    @classmethod
    def lowercase_username(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def bcrypt_byte_limit(cls, v: str) -> str:
        # bcrypt only reads the first 72 bytes
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password is too long")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=30)
    password: str = Field(..., max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None
    created_at: datetime
