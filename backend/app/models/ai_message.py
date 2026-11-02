from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiMessage(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (Index("idx_ai_session", "session_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32))
    slots: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False, server_default=text("'{}'"))
    fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
