import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class RecurringGroup(Base):
    __tablename__ = "recurring_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"), index=True)
    label: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(32))
    frequency: Mapped[str] = mapped_column(String(16))
    typical_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    last_seen_date: Mapped[date] = mapped_column(Date)
    transaction_ids: Mapped[str] = mapped_column(Text)  # JSON array of txn ids
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    session: Mapped["UploadSession"] = relationship(back_populates="recurring_groups")
