import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import settings as cfg
from ..constants import (
    THRESHOLD_AUTO_APPROVE,
    THRESHOLD_REVIEW,
    WEIGHT_FRESHERS,
    WEIGHT_LOCATION,
    WEIGHT_ROLE,
    WEIGHT_SKILLS,
)
from ..deps import get_current_user, get_db
from ..models.blacklist import CompanyBlacklist, KeywordBlacklist
from ..models.telegram import TelegramSettings
from ..models.user import User
from ..schemas.blacklist import (
    CompanyBlacklistCreate,
    CompanyBlacklistOut,
    KeywordBlacklistCreate,
    KeywordBlacklistOut,
)
from ..schemas.telegram import TelegramSettingsOut, TelegramSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


# --------------------------------------------------------------------------- #
# Settings overview (read-only config the dashboard displays)
# --------------------------------------------------------------------------- #
@router.get("")
def get_settings(_: User = Depends(get_current_user)) -> dict:
    return {
        "scan_interval_minutes": cfg.SCAN_INTERVAL_MINUTES,
        "test_mode": cfg.TEST_MODE,
        "data_retention_days": cfg.DATA_RETENTION_DAYS,
        "scoring_weights": {
            "freshers": WEIGHT_FRESHERS,
            "skills": WEIGHT_SKILLS,
            "location": WEIGHT_LOCATION,
            "role": WEIGHT_ROLE,
        },
        "thresholds": {
            "auto_approve": THRESHOLD_AUTO_APPROVE,
            "review": THRESHOLD_REVIEW,
        },
    }


# --------------------------------------------------------------------------- #
# Telegram settings (chat id + notification preferences; token is env-only)
# --------------------------------------------------------------------------- #
def _telegram(db: Session) -> TelegramSettings:
    s = db.get(TelegramSettings, 1)
    if s is None:
        s = TelegramSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _telegram_out(s: TelegramSettings) -> TelegramSettingsOut:
    out = TelegramSettingsOut.model_validate(s)
    out.configured = bool(cfg.TELEGRAM_BOT_TOKEN)
    return out


@router.get("/telegram", response_model=TelegramSettingsOut)
def get_telegram(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _telegram_out(_telegram(db))


@router.put("/telegram", response_model=TelegramSettingsOut)
def update_telegram(
    payload: TelegramSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = _telegram(db)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    write_audit(db, user.username, "telegram.settings_update", "telegram", payload=data)
    return _telegram_out(s)


# --------------------------------------------------------------------------- #
# Company blacklist
# --------------------------------------------------------------------------- #
@router.get("/blacklist/companies", response_model=list[CompanyBlacklistOut])
def list_company_blacklist(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(CompanyBlacklist).order_by(CompanyBlacklist.company).all()


@router.post(
    "/blacklist/companies",
    response_model=CompanyBlacklistOut,
    status_code=status.HTTP_201_CREATED,
)
def add_company_blacklist(
    payload: CompanyBlacklistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = CompanyBlacklist(company=payload.company, reason=payload.reason)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Company already blacklisted")
    db.refresh(row)
    write_audit(db, user.username, "blacklist.company.add", "company_blacklist", row.id, {"company": payload.company})
    return row


@router.delete("/blacklist/companies/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_company_blacklist(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(CompanyBlacklist, item_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    db.delete(row)
    db.commit()
    write_audit(db, user.username, "blacklist.company.remove", "company_blacklist", item_id)


# --------------------------------------------------------------------------- #
# Keyword blacklist
# --------------------------------------------------------------------------- #
@router.get("/blacklist/keywords", response_model=list[KeywordBlacklistOut])
def list_keyword_blacklist(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(KeywordBlacklist).order_by(KeywordBlacklist.keyword).all()


@router.post(
    "/blacklist/keywords",
    response_model=KeywordBlacklistOut,
    status_code=status.HTTP_201_CREATED,
)
def add_keyword_blacklist(
    payload: KeywordBlacklistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.applies_to not in ("title", "description", "both"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "applies_to must be title|description|both")
    row = KeywordBlacklist(
        keyword=payload.keyword, applies_to=payload.applies_to, reason=payload.reason
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Keyword already blacklisted")
    db.refresh(row)
    write_audit(db, user.username, "blacklist.keyword.add", "keyword_blacklist", row.id, {"keyword": payload.keyword})
    return row


@router.delete("/blacklist/keywords/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_keyword_blacklist(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(KeywordBlacklist, item_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    db.delete(row)
    db.commit()
    write_audit(db, user.username, "blacklist.keyword.remove", "keyword_blacklist", item_id)
