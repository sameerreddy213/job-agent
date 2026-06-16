from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..deps import get_current_user, get_db
from ..models.source import Source
from ..models.user import User
from ..schemas.source import SourceOut, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Source).order_by(Source.name).all()


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    src = db.get(Source, source_id)
    if src is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    data = payload.model_dump(exclude_unset=True)
    if "apply_policy" in data and data["apply_policy"] not in ("auto", "manual"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "apply_policy must be 'auto' or 'manual'")
    for field, value in data.items():
        setattr(src, field, value)
    db.commit()
    db.refresh(src)
    write_audit(db, user.username, "source.update", "source", source_id, data)
    return src
