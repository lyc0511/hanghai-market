from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.content import Content


class Post(Base):
    """校园墙帖子。公共字段（投稿人、标签、状态、驳回原因）在 contents，这里只放帖子特有的。

    匿名说明：投稿人只记录在 contents.owner_id，任何面向普通用户的接口都不返回它。
    """

    __tablename__ = "posts"
    __table_args__ = (Index("idx_posts_published", text("published_at DESC")),)

    content_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True
    )
    # 正文单独存：contents.summary 最多 300 字，帖子允许 500 字
    body: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 审核通过、真正上墙的时间；信息流按它排序（而不是投稿时间），先过审的排在前面
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # AI 预审结果：None 未预审 / ok 未发现问题 / attention 需要留意；只给管理员参考，不自动决定通过与否
    ai_level: Mapped[str | None] = mapped_column(String(16))
    ai_note: Mapped[str | None] = mapped_column(String(200))

    content: Mapped[Content] = relationship(back_populates="post")


class PostComment(Base):
    """帖子评论。status：online 正常 / deleted 本人删除 / offline 管理员下架。"""

    __tablename__ = "post_comments"
    __table_args__ = (Index("idx_post_comments_post", "post_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.content_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    reply_to_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("post_comments.id"))
    body: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="online")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PostLike(Base):
    """帖子点赞：联合主键保证一人对一条帖子只能点一次。"""

    __tablename__ = "post_likes"

    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.content_id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
