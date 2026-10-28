import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app import fake_model, ml_client, models, schemas
from app.auth import (
    DUMMY_HASH, create_access_token, get_current_user, get_optional_user,
    hash_password, verify_password,
)
from app.config import settings
from app.database import Base, engine, get_db
from app.ratelimit import (
    analyze_limit, client_ip, login_failures, register_limit, too_many,
)

log = logging.getLogger("sentio")


def _migrate() -> None:
    """Add columns that older databases are missing (create_all never alters tables)."""
    cols = {c["name"] for c in inspect(engine).get_columns("reviews")}
    if "user_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE reviews ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_reviews_user_id ON reviews (user_id)"))
        log.info("Added reviews.user_id column")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate()
    with Session(engine) as db:
        if not db.scalar(select(func.count()).select_from(models.Aspect)):
            db.add_all([
                models.Aspect(key=k, label=l) for k, l in models.ASPECT_KEYS
            ])
            db.commit()
    yield

app = FastAPI(
    title=settings.app_name,
    description="Aspect-based sentiment analysis of code-mixed Hinglish "
                "food delivery reviews.",
    version="0.2.0",
    lifespan=lifespan,
)

# Allowed frontends come from FRONTEND_ORIGINS in .env (Vite dev server + deployed site)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,          # tokens travel in a header, not cookies
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("Strict-Transport-Security", "max-age=31536000")
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        # the API only returns JSON, so nothing on it may load scripts or be framed
        h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if request.url.path.startswith("/v1/"):
        h.setdefault("Cache-Control", "no-store")
    return response


@app.get("/health")
def health():
    return {"status": "ok", "fake_model": settings.use_fake_model}


# ---------------- Auth ----------------

@app.post("/v1/auth/register", response_model=schemas.UserOut,
          status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(payload: schemas.RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Create a dashboard account. The password is stored only as a bcrypt hash."""
    register_limit.check_and_hit(client_ip(request))
    exists = db.scalar(
        select(models.User).where(models.User.username == payload.username)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = models.User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/v1/auth/login", response_model=schemas.TokenResponse, tags=["auth"])
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Check username + password and return a signed access token."""
    name = payload.username.strip().lower()
    keys = (f"ip:{client_ip(request)}", f"user:{name}")
    # Too many wrong passwords from this address or for this account: slow down guessing.
    if any(login_failures.blocked(k) for k in keys):
        raise too_many(login_failures.window)

    user = db.scalar(select(models.User).where(models.User.username == name))
    # Same message (and same bcrypt work) for "no such user" and "wrong password"
    # on purpose, so the API never reveals which usernames exist.
    ok = verify_password(payload.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not user.is_active or not ok:
        for k in keys:
            login_failures.hit(k)
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    login_failures.reset(f"user:{name}")

    return schemas.TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.jwt_expire_minutes * 60,
    )


@app.get("/v1/auth/me", response_model=schemas.UserOut, tags=["auth"])
def me(user: models.User = Depends(get_current_user)):
    """Who is logged in. The frontend calls this on page load."""
    return user


# ---------------- Analysis ----------------

def _model_version_row(db: Session, name: str) -> models.ModelVersion:
    """Find or create the model_versions row for the model that made a prediction,
    and mark it as the active one."""
    row = db.scalar(select(models.ModelVersion).where(models.ModelVersion.name == name))
    if row is None:
        row = models.ModelVersion(name=name)
        if not settings.use_fake_model:
            info = ml_client.model_info()
            row.base_model = info.get("base_model")
            row.train_size = info.get("train_size")
            row.macro_f1 = info.get("test_overall_macro_f1")
            row.per_class_f1 = {
                "aspect_detection_f1": info.get("test_aspect_detection_f1"),
                "aspect_sentiment_f1": info.get("test_aspect_sentiment_f1"),
            }
            row.notes = "Scores are on the frozen test split."
        else:
            row.notes = "Keyword placeholder. Not evaluated."
        db.add(row)
        db.flush()
    if not row.is_active:
        for other in db.scalars(select(models.ModelVersion).where(models.ModelVersion.is_active)):
            other.is_active = False
        row.is_active = True
    return row


@app.post("/v1/analyze", response_model=schemas.AnalyzeResponse)
def analyze(
    payload: schemas.AnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(get_optional_user),
):
    """Analyze one review with the active model (placeholder or trained).
    Open to everyone; when logged in, the review is saved to that user's history."""
    analyze_limit.check_and_hit(f"user:{user.id}" if user else f"ip:{client_ip(request)}")
    raw = fake_model.predict(payload.text) if settings.use_fake_model else ml_client.predict(payload.text)
    try:
        result = schemas.ModelOutput.model_validate(raw).model_dump()
    except ValidationError as e:
        log.warning("Model returned an unexpected shape: %s", e)
        raise HTTPException(status_code=502, detail="Model service gave an invalid answer")
    for a in result["aspects"]:      # drop spans that fall outside the text
        sp = a.get("span")
        if sp and not (len(sp) == 2 and 0 <= sp[0] < sp[1] <= len(payload.text)):
            a["span"] = None
    model_row = _model_version_row(db, result["model_version"])

    review = models.Review(
        user_id=user.id if user else None,
        raw_text=payload.text,
        normalized_text=result["normalized_text"],
        source_app=payload.source_app,
        lang_distribution=result["language_distribution"],
    )
    db.add(review)
    db.flush()

    analysis = models.Analysis(
        review_id=review.id,
        model_version_id=model_row.id,
        polarity=result["polarity"],
        confidence=result["confidence"],
        sarcasm=result["sarcasm"],
        token_attributions=result["tokens"],
        latency_ms=result["latency_ms"],
    )
    db.add(analysis)
    db.flush()

    aspect_rows = {a.key: a.id for a in db.scalars(select(models.Aspect))}
    for item in result["aspects"]:
        aspect_id = aspect_rows.get(item["aspect"])
        if aspect_id is None:
            continue
        db.add(models.AspectResult(
            analysis_id=analysis.id,
            aspect_id=aspect_id,
            polarity=item["polarity"],
            confidence=item["confidence"],
            span_start=item["span"][0] if item.get("span") else None,
            span_end=item["span"][1] if item.get("span") else None,
        ))

    db.commit()

    return schemas.AnalyzeResponse(
        id=analysis.id,
        text=payload.text,
        **{k: result[k] for k in (
            "normalized_text", "polarity", "confidence", "sarcasm",
            "language_distribution", "tokens", "aspects",
            "model_version", "latency_ms",
        )},
    )


@app.get("/v1/reviews", response_model=schemas.ReviewPage)
def list_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    polarity: schemas.Polarity | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """The logged-in user's own analysed reviews, newest first."""
    stmt = (select(models.Analysis).join(models.Review)
            .where(models.Review.user_id == user.id)
            .order_by(models.Analysis.id.desc()))
    if polarity:
        stmt = stmt.where(models.Analysis.polarity == polarity)

    total = db.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0
    rows = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return schemas.ReviewPage(
        items=[
            schemas.ReviewSummary(
                id=a.id,
                text=a.review.raw_text,
                polarity=a.polarity,
                confidence=a.confidence,
                created_at=a.created_at,
            )
            for a in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@app.get("/v1/reviews/{analysis_id}", response_model=schemas.AnalyzeResponse)
def get_review(
    analysis_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    a = db.get(models.Analysis, analysis_id)
    # someone else's review looks exactly like a missing one
    if a is None or a.review.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return schemas.AnalyzeResponse(
        id=a.id,
        text=a.review.raw_text,
        normalized_text=a.review.normalized_text or "",
        polarity=a.polarity,
        confidence=a.confidence,
        sarcasm=a.sarcasm,
        language_distribution=a.review.lang_distribution or {},
        tokens=a.token_attributions or [],
        aspects=[
            schemas.AspectVerdict(
                aspect=r.aspect.key,
                polarity=r.polarity,
                confidence=r.confidence or 0.0,
                span=[r.span_start, r.span_end]
                     if r.span_start is not None else None,
            )
            for r in a.aspects
        ],
        model_version=a.model_version.name if a.model_version else fake_model.MODEL_VERSION,
        latency_ms=a.latency_ms or 0,
    )


@app.get("/v1/insights/summary", response_model=schemas.InsightsSummary)
def insights(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Totals over the logged-in user's own reviews."""
    mine = models.Review.user_id == user.id
    total = db.scalar(
        select(func.count()).select_from(models.Analysis).join(models.Review).where(mine)
    ) or 0

    polarity_counts = {
        p: c for p, c in db.execute(
            select(models.Analysis.polarity, func.count())
            .join(models.Review).where(mine)
            .group_by(models.Analysis.polarity)
        )
    }

    rows = db.execute(
        select(models.Aspect.key, models.AspectResult.polarity, func.count())
        .join(models.AspectResult, models.AspectResult.aspect_id == models.Aspect.id)
        .join(models.Analysis, models.Analysis.id == models.AspectResult.analysis_id)
        .join(models.Review, models.Review.id == models.Analysis.review_id)
        .where(mine)
        .group_by(models.Aspect.key, models.AspectResult.polarity)
    ).all()

    buckets: dict[str, dict[str, int]] = {}
    for key, pol, count in rows:
        buckets.setdefault(key, {"positive": 0, "negative": 0, "neutral": 0})
        buckets[key][pol] = count

    breakdown = [
        schemas.AspectBreakdown(aspect=k, **v) for k, v in sorted(buckets.items())
    ]

    lang_totals: dict[str, float] = {}
    for (dist,) in db.execute(select(models.Review.lang_distribution).where(mine)):
        for k, v in (dist or {}).items():
            lang_totals[k] = lang_totals.get(k, 0.0) + v
    # share of all words, so the parts always add up to 100%
    n = sum(lang_totals.values()) or 1.0
    language_split = {k: round(v / n, 3) for k, v in lang_totals.items()}

    return schemas.InsightsSummary(
        total_reviews=total,
        polarity_counts=polarity_counts,
        aspect_breakdown=breakdown,
        language_split=language_split,
    )


@app.get("/v1/models", response_model=list[schemas.ModelInfo])
def list_models(db: Session = Depends(get_db)):
    return db.scalars(
        select(models.ModelVersion).order_by(models.ModelVersion.id.desc())
    ).all()
