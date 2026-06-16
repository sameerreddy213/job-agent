from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.profile import Profile
from ..models.user import User
from ..schemas.profile import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    profile = db.get(Profile, 1)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not set"
        )
    return profile


@router.put("", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1, **payload.model_dump())
        db.add(profile)
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
