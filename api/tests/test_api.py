from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import ml_client
from app.config import settings

ASPECTS = {"delivery_time", "food_quality", "packaging", "delivery_partner",
           "app_experience", "price_offers", "refund_support"}


# ---------------- health / models ----------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_models_lists_versions(client):
    client.post("/v1/analyze", json={"text": "khana achha tha"})
    rows = client.get("/v1/models").json()
    assert any(m["is_active"] for m in rows)
    assert sum(m["is_active"] for m in rows) == 1


# ---------------- register ----------------

def test_register_and_duplicate_is_case_insensitive(client):
    assert client.post("/v1/auth/register", json={"username": "Asha_1", "password": "longenough1"}).status_code == 201
    r = client.post("/v1/auth/register", json={"username": "asha_1", "password": "longenough1"})
    assert r.status_code == 409


@pytest.mark.parametrize("payload", [
    {"username": "ab", "password": "longenough1"},              # too short
    {"username": "a" * 31, "password": "longenough1"},          # too long
    {"username": "bad name", "password": "longenough1"},        # space
    {"username": "x';DROP", "password": "longenough1"},         # symbols
    {"username": "okname", "password": "short"},                # short password
    {"username": "okname2", "password": "ह" * 30},              # >72 bytes for bcrypt
    {"username": "okname3"},                                    # missing password
])
def test_register_rejects_bad_input(client, payload):
    assert client.post("/v1/auth/register", json=payload).status_code == 422


def test_password_is_never_returned(client):
    r = client.post("/v1/auth/register", json={"username": "secretcheck", "password": "longenough1"})
    assert "password" not in r.text and "hash" not in r.text


# ---------------- login / tokens ----------------

def test_login_ok_and_case_insensitive(client, user):
    name, pw, _ = user
    r = client.post("/v1/auth/login", json={"username": name.upper(), "password": pw})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


def test_login_wrong_password_and_unknown_user_look_identical(client, user):
    name, _, _ = user
    a = client.post("/v1/auth/login", json={"username": name, "password": "wrong-password"})
    b = client.post("/v1/auth/login", json={"username": "nobody_here", "password": "wrong-password"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_me(client, user):
    name, _, h = user
    assert client.get("/v1/auth/me", headers=h).json()["username"] == name


def _token(sub, secret=None, minutes=5, alg="HS256"):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(sub), "iat": now, "exp": now + timedelta(minutes=minutes)},
                      secret or settings.jwt_secret, algorithm=alg)


@pytest.mark.parametrize("header", [
    None,
    "Bearer not-a-jwt",
    "Bearer " + _token(1, secret="attacker-secret"),     # forged signature
    "Bearer " + _token(1, minutes=-1),                   # expired
    "Bearer " + _token(999999),                          # user does not exist
    "Basic dXNlcjpwYXNz",                                # wrong scheme
])
def test_protected_routes_reject_bad_tokens(client, header):
    h = {"Authorization": header} if header else {}
    for path in ("/v1/auth/me", "/v1/reviews", "/v1/insights/summary", "/v1/reviews/1"):
        assert client.get(path, headers=h).status_code in (401, 403), (path, header)


def test_alg_none_token_rejected(client):
    unsigned = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, key=None, algorithm="none")
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {unsigned}"}).status_code == 401


# ---------------- analyze ----------------

def _check_result(text, d):
    assert d["text"] == text
    assert d["polarity"] in {"positive", "negative", "neutral"}
    assert 0 <= d["confidence"] <= 1
    for a in d["aspects"]:
        assert a["aspect"] in ASPECTS
        assert a["polarity"] in {"positive", "negative", "neutral"}
        if a["span"] is not None:
            s, e = a["span"]
            assert 0 <= s < e <= len(text)


@pytest.mark.parametrize("text", [
    "Khana bahut tasty tha par delivery boy rude tha",
    "खाना ठंडा था 😡 delivery late",
    "'; DROP TABLE reviews; --",
    "<script>alert(1)</script> packaging leak",
    "a" * 2000,
])
def test_analyze_accepts_real_and_hostile_text(client, text):
    r = client.post("/v1/analyze", json={"text": text})
    assert r.status_code == 200, r.text
    _check_result(text, r.json())


@pytest.mark.parametrize("payload", [{"text": ""}, {"text": "a" * 2001}, {}, {"text": 123}])
def test_analyze_rejects_bad_input(client, payload):
    assert client.post("/v1/analyze", json=payload).status_code == 422


def test_analyze_rejects_whitespace_only(client):
    assert client.post("/v1/analyze", json={"text": "   \n\t "}).status_code == 422


# ---------------- reviews / insights ----------------

def test_reviews_pagination_and_filter(client, user):
    _, _, h = user
    for t in ["bahut bekar app", "khana mast tha", "order late aaya"]:
        client.post("/v1/analyze", json={"text": t}, headers=h)
    page = client.get("/v1/reviews?page=1&page_size=2", headers=h).json()
    assert len(page["items"]) <= 2 and page["total"] >= 3
    neg = client.get("/v1/reviews?polarity=negative", headers=h).json()
    assert all(i["polarity"] == "negative" for i in neg["items"])


@pytest.mark.parametrize("q", ["page=0", "page_size=0", "page_size=101", "page=-1"])
def test_reviews_bad_paging(client, user, q):
    assert client.get(f"/v1/reviews?{q}", headers=user[2]).status_code == 422


def test_review_detail_and_404(client, user):
    _, _, h = user
    rid = client.post("/v1/analyze", json={"text": "packaging tuti hui thi"}, headers=h).json()["id"]
    assert client.get(f"/v1/reviews/{rid}", headers=h).status_code == 200
    assert client.get("/v1/reviews/987654", headers=h).status_code == 404


def test_insights_counts_add_up(client, user):
    _, _, h = user
    d = client.get("/v1/insights/summary", headers=h).json()
    assert sum(d["polarity_counts"].values()) == d["total_reviews"]
    if d["language_split"]:
        assert abs(sum(d["language_split"].values()) - 1) < 0.05


# ---------------- CORS ----------------

@pytest.mark.parametrize("origin,allowed", [
    ("http://localhost:5173", True), ("https://sentio.example.app", True), ("https://evil.example.com", False)])
def test_cors(client, origin, allowed):
    r = client.options("/v1/analyze", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    assert (r.headers.get("access-control-allow-origin") == origin) is allowed


# ---------------- model service failures ----------------

@pytest.fixture
def real_model_mode(monkeypatch):
    monkeypatch.setattr(settings, "use_fake_model", False)
    monkeypatch.setattr(ml_client, "_health_cache", None)
    yield


def test_model_service_down_gives_503(client, real_model_mode, monkeypatch):
    monkeypatch.setattr(settings, "ml_service_url", "http://127.0.0.1:9")
    r = client.post("/v1/analyze", json={"text": "khana achha tha"})
    assert r.status_code == 503


def test_model_service_garbage_gives_502_not_500(client, real_model_mode, monkeypatch):
    monkeypatch.setattr(ml_client, "predict", lambda *a, **k: {"unexpected": "shape"})
    r = client.post("/v1/analyze", json={"text": "khana achha tha"})
    assert r.status_code == 502


# ---------------- batch ----------------

def test_batch_analyze_in_order_and_saved(client, user):
    _, _, h = user
    texts = ["khana thanda tha", "  delivery fast thi  ", "refund nahi mila", "app crash hota hai"]
    r = client.post("/v1/analyze/batch", json={"texts": texts}, headers=h)
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    assert [x["text"] for x in res] == [t.strip() for t in texts]
    for x in res:
        _check_result(x["text"], x)
    assert client.get("/v1/reviews", headers=h).json()["total"] == 4


@pytest.mark.parametrize("payload", [{"texts": []}, {"texts": ["ok"] * 51}, {"texts": ["ok", "   "]},
                                     {"texts": ["a" * 2001]}, {"texts": "not a list"}, {}])
def test_batch_rejects_bad_input(client, user, payload):
    assert client.post("/v1/analyze/batch", json=payload, headers=user[2]).status_code == 422


def test_batch_needs_login(client):
    assert client.post("/v1/analyze/batch", json={"texts": ["khana mast"]}).status_code == 401
    assert client.post("/v1/analyze/batch", json={"texts": ["khana mast"]},
                       headers={"Authorization": "Bearer nope"}).status_code == 401


def test_batch_rate_limited(client, user):
    codes = [client.post("/v1/analyze/batch", json={"texts": ["khana mast"]}, headers=user[2]).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429


def test_batch_model_wrong_length_is_502(client, user, real_model_mode, monkeypatch):
    monkeypatch.setattr(ml_client, "predict_batch", lambda texts: [])
    assert client.post("/v1/analyze/batch", json={"texts": ["a", "b"]}, headers=user[2]).status_code == 502
