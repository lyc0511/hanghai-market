from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.user import User


class TradeIntent(Base):
    __tablename__ = "trade_intents"
    __table_args__ = (
        # 同一买家对同一物品只能有一条“进行中/已成交”的意向
        Index(
            "uq_intent_active",
            "item_id",
            "buyer_id",
            unique=True,
            postgresql_where=text("status IN ('pending','accepted','completed')"),
        ),
        Index("idx_intents_buyer", "buyer_id", "status"),
        Index("idx_intents_seller", "seller_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("items.content_id"), nullable=False)
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    message: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    contact_revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=utcnow
    )

    item: Mapped[Item] = relationship()
    buyer: Mapped[User] = relationship(foreign_keys=[buyer_id])
    seller: Mapped[User] = relationship(foreign_keys=[seller_id])
