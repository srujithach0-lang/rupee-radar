import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"), unique=True, index=True)
    metrics: Mapped[str] = mapped_column(Text)  # JSON
    insights: Mapped[str] = mapped_column(Text)  # JSON array
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["UploadSession"] = relationship(back_populates="analysis_result")
