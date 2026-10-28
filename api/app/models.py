from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# The seven aspects, fixed. Used to seed the aspects table.
ASPECT_KEYS = [
    ("delivery_time",    "Delivery time"),
    ("food_quality",     "Food quality"),
    ("packaging",        "Packaging"),
    ("delivery_partner", "Delivery partner"),
    ("app_experience",   "App experience"),
    ("price_offers",     "Price and offers"),
    ("refund_support",   "Refund and support"),
]


class User(Base):
    """A dashboard user (e.g. an analyst at the food delivery company)."""
    __tablename__ = "users"

    id:            Mapped[int]  = mapped_column(Integer, primary_key=True)
    username:      Mapped[str]  = mapped_column(String(30), unique=True, nullable=False)
    # bcrypt hash only. The plain password is never stored.
    password_hash: Mapped[str]  = mapped_column(String(100), nullable=False)
    full_name:     Mapped[str | None] = mapped_column(String(100))
    is_active:     Mapped[bool] = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Review(Base):
    __tablename__ = "reviews"

    id:              Mapped[int]  = mapped_column(Integer, primary_key=True)
    raw_text:        Mapped[str]  = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    source_app:      Mapped[str | None] = mapped_column(String(50))
    star_rating:     Mapped[int | None] = mapped_column(Integer)
    # {"en": 0.33, "hi_roman": 0.60, "emoji": 0.07}
    lang_distribution: Mapped[dict | None] = mapped_column(JSONB)
    # hash of the reviewer handle, never the handle itself
    author_hash:     Mapped[str | None] = mapped_column(String(64))
    # who submitted it (None = analysed without logging in; visible to nobody)
    user_id:         Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="review")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    name:       Mapped[str] = mapped_column(String(100), nullable=False)
    base_model: Mapped[str | None] = mapped_column(String(100))
    train_size: Mapped[int | None] = mapped_column(Integer)
    macro_f1:   Mapped[float | None] = mapped_column(Float)
    per_class_f1: Mapped[dict | None] = mapped_column(JSONB)
    notes:      Mapped[str | None] = mapped_column(Text)
    is_active:  Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id:        Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), nullable=False)
    # every prediction is traceable to the model that made it
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id")
    )
    polarity:   Mapped[str]   = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sarcasm:    Mapped[bool]  = mapped_column(Boolean, default=False)
    # [{"text": "ghatiya", "lang": "hi_roman", "weight": -0.78}, ...]
    token_attributions: Mapped[list | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    review:  Mapped["Review"] = relationship(back_populates="analyses")
    model_version: Mapped["ModelVersion | None"] = relationship()
    aspects: Mapped[list["AspectResult"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Aspect(Base):
    __tablename__ = "aspects"

    id:    Mapped[int] = mapped_column(Integer, primary_key=True)
    key:   Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)


class AspectResult(Base):
    __tablename__ = "aspect_results"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    aspect_id:   Mapped[int] = mapped_column(ForeignKey("aspects.id"), nullable=False)
    polarity:    Mapped[str] = mapped_column(String(10), nullable=False)
    confidence:  Mapped[float | None] = mapped_column(Float)
    span_start:  Mapped[int | None] = mapped_column(Integer)
    span_end:    Mapped[int | None] = mapped_column(Integer)

    analysis: Mapped["Analysis"] = relationship(back_populates="aspects")
    aspect:   Mapped["Aspect"]   = relationship()
