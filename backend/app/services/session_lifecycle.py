from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import UploadSession


def is_session_expired(session: UploadSession) -> bool:
    if not session.expires_at:
        return False
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expires


def get_active_session_or_404(db: Session, session_id: str) -> UploadSession:
    session = db.query(UploadSession).filter(UploadSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if is_session_expired(session):
        raise HTTPException(status_code=404, detail="Session expired")
    return session


def delete_session(db: Session, session: UploadSession) -> None:
    db.delete(session)
    db.commit()
