from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.club import Club
    from app.models.content import Content


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("capacity > 0"),
        Index("idx_activities_start", "start_time"),
    )

    content_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    club_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clubs.content_id", ondelete="CASCADE"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String(128), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    enrolled_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    signup_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    content: Mapped[Content] = relationship(back_populates="activity")
    club: Mapped[Club] = relationship(back_populates="activities")
