"""Password hashing (bcrypt) + JWT helpers.

Uses the `bcrypt` library directly rather than passlib — passlib 1.7.x breaks
against modern bcrypt releases during backend detection. bcrypt hashes only the
first 72 bytes of the input, so we truncate explicitly to avoid ValueErrors.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings

_MAX = 72  # bcrypt input limit (bytes)


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_MAX], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
