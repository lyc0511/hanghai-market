from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivitySignup(Base):
    __tablename__ = "activity_signups"
    __table_args__ = (UniqueConstraint("activity_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("activities.content_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="signed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
