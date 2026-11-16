from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow

if TYPE_CHECKING:
    from app.models.activity import Activity
    from app.models.category import Category
    from app.models.club import Club
    from app.models.item import Item
    from app.models.post import Post
    from app.models.user import User


class Content(Base):
    """统一内容表：物品 / 社团 / 活动 / 帖子 的公共字段，子表按 content_id 一对一扩展。"""

    __tablename__ = "contents"
    __table_args__ = (
        Index("idx_contents_type_status", "type", "status"),
        Index("idx_contents_owner", "owner_id"),
        Index("idx_contents_created", text("created_at DESC")),
        Index("idx_contents_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(300))
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    campus_area: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="online")
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    search_text: Mapped[str | None] = mapped_column(Text)
    # 向量以 JSON 数组文本存储（如 "[0.12, -0.03, ...]"），不使用 pgvector
    embedding_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="contents")
    category: Mapped[Category | None] = relationship()
    item: Mapped[Item | None] = relationship(back_populates="content", uselist=False, cascade="all, delete-orphan")
    club: Mapped[Club | None] = relationship(back_populates="content", uselist=False, cascade="all, delete-orphan")
    activity: Mapped[Activity | None] = relationship(
        back_populates="content", uselist=False, cascade="all, delete-orphan"
    )
    post: Mapped[Post | None] = relationship(back_populates="content", uselist=False, cascade="all, delete-orphan")
