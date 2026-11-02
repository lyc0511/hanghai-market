from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.content import Content
    from app.models.user import User


class Club(Base):
    __tablename__ = "clubs"

    content_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    logo_url: Mapped[str | None] = mapped_column(Text)
    club_type: Mapped[str] = mapped_column(String(32), nullable=False)
    founded_year: Mapped[int | None] = mapped_column(SmallInteger)
    president_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    recruit_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="closed")
    recruit_start: Mapped[date | None] = mapped_column(Date)
    recruit_end: Mapped[date | None] = mapped_column(Date)
    recruit_note: Mapped[str | None] = mapped_column(String(300))

    content: Mapped[Content] = relationship(back_populates="club")
    president: Mapped[User | None] = relationship()
    activities: Mapped[list[Activity]] = relationship(back_populates="club")
