import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..constants import ALLOWED_CATEGORIES
from ..deps import get_current_user, get_db
from ..materials import GenerationError, generate_materials
from ..models.job import Job
from ..models.material import Material
from ..models.user import User
from ..schemas.material import MaterialOut
from ..workflow import InvalidTransition, State, transition

router = APIRouter(prefix="/jobs", tags=["materials"])

_MEDIA = {
    "txt": ("text/plain", "txt_path", "packet.txt"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx_path",
        "packet.docx",
    ),
    "pdf": ("application/pdf", "pdf_path", "packet.pdf"),
}


def _to_out(material: Material) -> MaterialOut:
    formats = [
        fmt for fmt, (_, attr, _) in _MEDIA.items() if getattr(material, attr) and os.path.exists(getattr(material, attr))
    ]
    out = MaterialOut.model_validate(material)
    out.formats = formats
    return out


@router.post("/{job_id}/materials/generate", response_model=MaterialOut)
def generate(
    job_id: uuid.UUID,
    cover_letter: bool = Query(True),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if category is not None and category not in ALLOWED_CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown category '{category}'")
    try:
        material = generate_materials(db, job, cover_letter=cover_letter, category_override=category)
    except GenerationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    write_audit(
        db, user.username, "materials.generate", "job", job_id,
        {"category": material.resume_category, "cover_letter": cover_letter},
    )
    # Advance an approved job along the workflow when materials are produced.
    if job.status == State.APPROVED:
        try:
            transition(db, job, State.MATERIALS_GENERATED, actor=user.username, reason="materials generated")
        except InvalidTransition:
            pass
    return _to_out(material)


@router.get("/{job_id}/materials", response_model=MaterialOut)
def get_materials(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    material = db.query(Material).filter(Material.job_id == job_id).first()
    if material is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No materials generated for this job")
    return _to_out(material)


@router.get("/{job_id}/materials/download/{fmt}")
def download(
    job_id: uuid.UUID,
    fmt: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if fmt not in _MEDIA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Format must be txt, docx, or pdf")
    material = db.query(Material).filter(Material.job_id == job_id).first()
    if material is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No materials generated for this job")
    media_type, attr, filename = _MEDIA[fmt]
    path = getattr(material, attr)
    if not path or not os.path.exists(path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{fmt} export not found")
    return FileResponse(path, media_type=media_type, filename=filename)
