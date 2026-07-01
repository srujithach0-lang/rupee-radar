import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import SessionStatus


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default=SessionStatus.PENDING)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_warnings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    row_count: Mapped[int] = mapped_column(Integer, default=0)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    recurring_groups: Mapped[list["RecurringGroup"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    analysis_result: Mapped["AnalysisResult | None"] = relationship(back_populates="session", cascade="all, delete-orphan", uselist=False)
