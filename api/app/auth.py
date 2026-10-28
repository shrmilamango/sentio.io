"""
Login helpers: password hashing, token creation, and the dependency that
protects routes.

Flow:
  register -> password is bcrypt-hashed and stored
  login    -> password checked against the hash, a signed JWT is returned
  request  -> frontend sends "Authorization: Bearer <token>",
              get_current_user() verifies it and loads the user
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import get_db

ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Checked when the username does not exist, so a failed login always takes
# the same time and timing cannot reveal which usernames are registered.
DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _user_from_token(token: str, db: Session) -> models.User | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM],
                             options={"require": ["exp", "sub"]})
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    user = db.get(models.User, user_id)
    return user if user is not None and user.is_active else None


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Add `user = Depends(get_current_user)` to any route to require login."""
    user = _user_from_token(creds.credentials, db) if creds else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User | None:
    """The logged-in user if a valid token was sent, otherwise None (no error)."""
    return _user_from_token(creds.credentials, db) if creds else None
