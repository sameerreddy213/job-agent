import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..constants import ALLOWED_CATEGORIES
from ..deps import get_current_user, get_db
from ..intelligence import categorize_resume, extract_skills, parse_resume_file
from ..models.resume import Resume, ResumeVersion
from ..models.user import User
from ..schemas.resume import (
    ResumeDetailOut,
    ResumeOut,
    ResumeSummaryOut,
    ResumeVersionOut,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _current_version(resume: Resume) -> ResumeVersion | None:
    for v in resume.versions:
        if v.is_current:
            return v
    return None


def _to_resume_out(resume: Resume) -> ResumeOut:
    cv = _current_version(resume)
    return ResumeOut(
        id=resume.id,
        category=resume.category,
        is_active=resume.is_active,
        created_at=resume.created_at,
        current_version=ResumeVersionOut.model_validate(cv) if cv else None,
    )


@router.get("", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    resumes = db.query(Resume).order_by(Resume.category).all()
    return [_to_resume_out(r) for r in resumes]


@router.get("/summary", response_model=list[ResumeSummaryOut])
def resume_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    out: list[ResumeSummaryOut] = []
    for resume in db.query(Resume).order_by(Resume.category).all():
        cv = _current_version(resume)
        out.append(
            ResumeSummaryOut(
                category=resume.category,
                current_version=ResumeVersionOut.model_validate(cv) if cv else None,
                previous_versions=max(0, len(resume.versions) - 1),
                last_updated=cv.upload_date if cv else None,
            )
        )
    return out


@router.get("/{category}/versions", response_model=ResumeDetailOut)
def list_versions(
    category: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    resume = db.query(Resume).filter(Resume.category == category).first()
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume category not found")
    cv = _current_version(resume)
    return ResumeDetailOut(
        id=resume.id,
        category=resume.category,
        is_active=resume.is_active,
        created_at=resume.created_at,
        current_version=ResumeVersionOut.model_validate(cv) if cv else None,
        versions=[ResumeVersionOut.model_validate(v) for v in resume.versions],
    )


@router.post(
    "/{category}/versions",
    response_model=ResumeDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_version(
    category: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown category '{category}'")

    resume = db.query(Resume).filter(Resume.category == category).first()
    if resume is None:
        resume = Resume(category=category)
        db.add(resume)
        db.flush()  # get resume.id

    next_version = (
        db.query(func.coalesce(func.max(ResumeVersion.version_number), 0))
        .filter(ResumeVersion.resume_id == resume.id)
        .scalar()
        + 1
    )

    # Validate type + size before persisting.
    safe_name = os.path.basename(file.filename or f"resume_{uuid.uuid4().hex}")
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file type '{ext or 'unknown'}' (use PDF, DOC, DOCX, or TXT)",
        )
    data = file.file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Resume exceeds the 5 MB limit")

    # Persist the uploaded file to the resumes volume (git-ignored on disk).
    cat_dir = os.path.join(settings.RESUME_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    dest = os.path.join(cat_dir, f"v{next_version}_{safe_name}")
    with open(dest, "wb") as out:
        out.write(data)

    # Phase 5A: parse the resume and extract skills + detected category (rule engine).
    text = parse_resume_file(dest)
    skills = extract_skills(text)
    detected_category, cat_confidence = categorize_resume(text, skills)

    # Demote previous current version, add the new one as current.
    for v in resume.versions:
        v.is_current = False

    version = ResumeVersion(
        resume_id=resume.id,
        version_number=next_version,
        file_path=dest,
        skills_detected=skills,
        role_category=category,
        detected_category=detected_category,
        categorization_confidence=cat_confidence,
        is_current=True,
    )
    db.add(version)
    db.commit()
    db.refresh(resume)
    return list_versions(category, db, _)  # type: ignore[arg-type]


@router.post("/{category}/rollback/{version_number}", response_model=ResumeDetailOut)
def rollback(
    category: str,
    version_number: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.category == category).first()
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume category not found")

    target = next((v for v in resume.versions if v.version_number == version_number), None)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")

    for v in resume.versions:
        v.is_current = v.version_number == version_number
    db.commit()
    db.refresh(resume)
    return list_versions(category, db, _)  # type: ignore[arg-type]
