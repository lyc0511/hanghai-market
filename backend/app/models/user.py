from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.content import Content


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    student_no: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nickname: Mapped[str] = mapped_column(String(30), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    campus_area: Mapped[str | None] = mapped_column(String(32))
    wechat_id_enc: Mapped[str | None] = mapped_column(Text)
    wechat_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="student")
    auth_source: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=utcnow
    )

    contents: Mapped[list[Content]] = relationship(back_populates="owner")
