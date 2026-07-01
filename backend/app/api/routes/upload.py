import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import UploadSession
from app.models.enums import SessionStatus
from app.schemas.session import SessionResponse, UploadResponse
from app.services.pipeline import delete_upload_temp, run_pipeline, save_upload_temp

router = APIRouter(tags=["upload"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    settings = get_settings()
    filename = file.filename or "statement.csv"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. Upload HDFC/ICICI CSV, a generic CSV, or Excel (.xlsx). "
                "See docs/sample-statement-template.csv for the expected format."
            ),
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_size_mb} MB limit")

    session = UploadSession(
        filename=filename,
        file_type=ext.lstrip("."),
        status=SessionStatus.PENDING.value,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    temp_path: str | None = None
    try:
        temp_path = save_upload_temp(content, filename)
        run_pipeline(db, session, content, filename)
    finally:
        if temp_path:
            delete_upload_temp(temp_path)

    db.refresh(session)
    if session.status == SessionStatus.FAILED.value:
        raise HTTPException(status_code=422, detail=session.error_message or "Failed to process statement")

    return UploadResponse(session_id=session.id, status=session.status)
