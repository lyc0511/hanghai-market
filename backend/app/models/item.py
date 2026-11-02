from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.content import Content


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (Index("idx_items_price", "price"),)

    content_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default=text("0"))
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    condition: Mapped[str] = mapped_column(String(16), nullable=False, server_default="good")
    images: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    content: Mapped[Content] = relationship(back_populates="item")
