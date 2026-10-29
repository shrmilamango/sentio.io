"""
Client for the Sentio model service (ML/serve.py, port 8001).

Used when USE_FAKE_MODEL=False. Standard library only, no extra install.
"""
import json
import logging
import urllib.error
import urllib.request

from fastapi import HTTPException

from app.config import settings

log = logging.getLogger("sentio")
_health_cache: dict | None = None
# Direct connection, no system proxy lookup. On Windows, urllib's proxy check
# does slow DNS lookups that added ~2 s to every prediction.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _call(method: str, path: str, payload: dict | None = None, timeout: float = 30.0) -> dict:
    # On Windows "localhost" tries IPv6 (::1) first and waits ~2 s before falling
    # back to 127.0.0.1, where the model service listens. Go straight there.
    base = settings.ml_service_url.rstrip("/").replace("://localhost", "://127.0.0.1")
    url = base + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json",
               # skip ngrok's browser warning page (free plan)
               "ngrok-skip-browser-warning": "1"}
    if settings.ml_service_token:
        headers["X-Sentio-Token"] = settings.ml_service_token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        # full details go to the server log only; the visitor gets a plain message
        log.warning("Model service call %s %s failed: %s", method, url, e)
        raise HTTPException(status_code=503, detail="Model service unavailable")
    except ValueError as e:  # not JSON (e.g. an ngrok error page)
        log.warning("Model service %s returned non-JSON: %s", url, e)
        raise HTTPException(status_code=502, detail="Model service gave an invalid answer")


def predict(text: str) -> dict:
    return _call("POST", "/predict", {"text": text})


def predict_batch(texts: list[str]) -> list[dict]:
    out = _call("POST", "/predict_batch", {"texts": texts}, timeout=180.0)
    return out.get("results") if isinstance(out, dict) else None


def model_info() -> dict:
    """Name and test scores of the model being served (cached)."""
    global _health_cache
    if _health_cache is None:
        _health_cache = _call("GET", "/health", timeout=5.0)
    return _health_cache
