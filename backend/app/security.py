"""Password hashing (argon2) and JWT token helpers."""
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from .config import settings

ALGORITHM = "HS256"
_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _encode(subject: str, ttl: timedelta, token_type: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    return _encode(subject, timedelta(minutes=settings.JWT_ACCESS_TTL_MIN), "access")


def new_jti() -> str:
    return uuid.uuid4().hex


def create_refresh_token(subject: str, jti: str) -> str:
    return _encode(
        subject, timedelta(days=settings.JWT_REFRESH_TTL_DAYS), "refresh", {"jti": jti}
    )


def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
