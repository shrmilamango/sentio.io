import time

import pytest
from sqlalchemy import create_engine, inspect, text

from app import ml_client, ratelimit
from app.config import Settings, settings


# ---------- each user sees only their own reviews ----------

def test_users_cannot_see_each_others_reviews(client, user):
    _, _, alice = user
    bob = None
    client.post("/v1/auth/register", json={"username": "bob_iso", "password": "longenough1"})
    bob = {"Authorization": "Bearer " + client.post(
        "/v1/auth/login", json={"username": "bob_iso", "password": "longenough1"}).json()["access_token"]}

    rid = client.post("/v1/analyze", json={"text": "alice ka private review, khana thanda"}, headers=alice).json()["id"]
    anon = client.post("/v1/analyze", json={"text": "anonymous review bekar"}).json()["id"]

    assert client.get(f"/v1/reviews/{rid}", headers=alice).status_code == 200
    assert client.get(f"/v1/reviews/{rid}", headers=bob).status_code == 404       # not 403: no hint it exists
    assert client.get(f"/v1/reviews/{anon}", headers=bob).status_code == 404
    bob_items = client.get("/v1/reviews", headers=bob).json()["items"]
    assert all("alice" not in i["text"] and "anonymous" not in i["text"] for i in bob_items)
    assert client.get("/v1/insights/summary", headers=bob).json()["total_reviews"] == 0


def test_bad_polarity_filter_is_rejected(client, user):
    assert client.get("/v1/reviews?polarity=' OR 1=1 --", headers=user[2]).status_code == 422


# ---------- brute force / spam ----------

def test_login_locks_after_10_failures(client, user):
    name, pw, _ = user
    for _ in range(10):
        assert client.post("/v1/auth/login", json={"username": name, "password": "nope-nope"}).status_code == 401
    r = client.post("/v1/auth/login", json={"username": name, "password": pw})   # even the right password
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_successful_login_does_not_count_as_failure(client, user):
    name, pw, _ = user
    for _ in range(15):
        assert client.post("/v1/auth/login", json={"username": name, "password": pw}).status_code == 200


def test_register_limited_per_ip(client):
    codes = [client.post("/v1/auth/register", json={"username": f"spam{i}", "password": "longenough1"}).status_code
             for i in range(7)]
    assert codes[:5] == [201] * 5 and codes[5:] == [429, 429]


def test_analyze_limited_per_ip(client):
    codes = [client.post("/v1/analyze", json={"text": "khana mast"}).status_code for _ in range(32)]
    assert codes.count(200) == 30 and codes[-1] == 429


def test_login_timing_does_not_reveal_usernames(client, user):
    name, _, _ = user
    def t(u):
        s = time.perf_counter(); client.post("/v1/auth/login", json={"username": u, "password": "wrong-pass"})
        return time.perf_counter() - s
    known = min(t(name) for _ in range(3)); ratelimit.login_failures.clear()
    unknown = min(t("ghost_user_x") for _ in range(3))
    assert unknown > known * 0.5          # both pay for a bcrypt check


def test_huge_login_payload_rejected(client):
    assert client.post("/v1/auth/login", json={"username": "a", "password": "x" * 10_000}).status_code == 422


# ---------- secrets / errors / headers ----------

def test_weak_jwt_secret_is_replaced():
    assert len(Settings(jwt_secret="change-me-in-env").jwt_secret) >= 32
    assert len(Settings(jwt_secret="").jwt_secret) >= 32
    strong = "x" * 40
    assert Settings(jwt_secret=strong).jwt_secret == strong


def test_503_does_not_leak_internal_url(client, monkeypatch):
    monkeypatch.setattr(settings, "use_fake_model", False)
    monkeypatch.setattr(settings, "ml_service_url", "http://10.9.8.7:1")
    monkeypatch.setattr(ml_client, "_health_cache", None)
    r = client.post("/v1/analyze", json={"text": "khana achha tha"})
    assert r.status_code == 503 and "10.9.8.7" not in r.text


def test_token_sent_to_model_service(monkeypatch):
    seen = {}
    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return b"{}"
    def fake_urlopen(req, timeout):
        seen.update(req.headers); return Resp()
    monkeypatch.setattr(settings, "ml_service_token", "s3cret")
    monkeypatch.setattr(ml_client.urllib.request, "urlopen", fake_urlopen)
    ml_client._call("GET", "/health")
    assert seen.get("X-sentio-token") == "s3cret"


def test_model_spans_outside_text_are_dropped(client, monkeypatch):
    from app import fake_model
    real = fake_model.predict
    def bad_span(text):
        out = real(text)
        out["aspects"] = [{"aspect": "food_quality", "polarity": "negative", "confidence": 0.9, "span": [5, 9999]}]
        return out
    monkeypatch.setattr(fake_model, "predict", bad_span)
    d = client.post("/v1/analyze", json={"text": "khana thanda tha"}).json()
    assert d["aspects"][0]["span"] is None


def test_security_headers(client):
    h = client.get("/health").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "default-src 'none'" in h["content-security-policy"]
    assert client.get("/docs").status_code == 200        # Swagger still works


def test_cors_does_not_allow_credentials_or_odd_methods(client):
    r = client.options("/v1/analyze", headers={"Origin": "http://localhost:5173",
                                               "Access-Control-Request-Method": "DELETE"})
    assert r.status_code == 400
    assert "access-control-allow-credentials" not in r.headers


# ---------- an older database gets the new column ----------

def test_migration_adds_user_id(tmp_path, monkeypatch):
    from app import main
    eng = create_engine(f"sqlite:///{tmp_path/'old.db'}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        c.execute(text("CREATE TABLE reviews (id INTEGER PRIMARY KEY, raw_text TEXT NOT NULL)"))
    monkeypatch.setattr(main, "engine", eng)
    main._migrate(); main._migrate()          # safe to run twice
    assert "user_id" in {c["name"] for c in inspect(eng).get_columns("reviews")}
