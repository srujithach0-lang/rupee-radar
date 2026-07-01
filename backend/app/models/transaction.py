import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("upload_sessions.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    description_raw: Mapped[str] = mapped_column(Text)
    description_clean: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    type: Mapped[str] = mapped_column(String(16))
    balance: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    category_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    category_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payment_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["UploadSession"] = relationship(back_populates="transactions")
