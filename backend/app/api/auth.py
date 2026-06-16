import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import ratelimit
from ..audit import write_audit
from ..deps import get_current_user, get_db
from ..models.auth_token import RefreshToken
from ..models.user import User
from ..schemas.auth import RefreshRequest, TokenPair, UserOut
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    new_jti,
    refresh_expiry,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_pair(db: Session, user: User, family_id: uuid.UUID | None = None) -> TokenPair:
    jti = new_jti()
    family = family_id or uuid.uuid4()
    db.add(
        RefreshToken(jti=jti, user_id=user.id, family_id=family, expires_at=refresh_expiry())
    )
    db.commit()
    return TokenPair(
        access_token=create_access_token(user.username),
        refresh_token=create_refresh_token(user.username, jti),
    )


def _revoke_all_user_tokens(db: Session, user_id: uuid.UUID) -> int:
    """Revoke every active refresh token for a user. Returns count revoked."""
    count = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .update({RefreshToken.revoked: True})
    )
    db.commit()
    return count


@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    key = form.username.lower()
    if ratelimit.is_locked(key):
        write_audit(db, key, "login.locked", "user", payload={"reason": "rate_limit"})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        )

    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        ratelimit.record_failure(key)
        write_audit(db, key, "login.failed", "user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    ratelimit.reset(key)
    pair = _issue_pair(db, user)
    write_audit(db, user.username, "login.success", "user", user.id)
    return pair


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("wrong token type")
        subject = payload["sub"]
        jti = payload["jti"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    token_row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    now = datetime.now(timezone.utc)

    if token_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # --- Reuse detection ---------------------------------------------------- #
    # A revoked token presented again means it was already rotated (or the user
    # logged out). Treat as a compromised family: revoke ALL of the user's
    # active tokens, audit, and force re-authentication.
    if token_row.revoked:
        revoked = _revoke_all_user_tokens(db, token_row.user_id)
        write_audit(
            db,
            subject,
            "security.refresh_reuse",
            "refresh_token",
            token_row.id,
            {"family_id": str(token_row.family_id), "tokens_revoked": revoked},
        )
        try:
            from ..telegram import notify_security

            notify_security(db, subject, now)
        except Exception:  # noqa: BLE001 — notification must never block auth
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions revoked; please sign in again.",
        )

    if token_row.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.query(User).filter(User.username == subject).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")

    # Rotate within the same family: revoke the presented token, issue a fresh pair.
    token_row.revoked = True
    db.commit()
    return _issue_pair(db, user, family_id=token_row.family_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        jti = payload.get("jti")
    except Exception:
        return  # idempotent: invalid token = already logged out
    if jti:
        token_row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if token_row and not token_row.revoked:
            token_row.revoked = True
            db.commit()


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current
