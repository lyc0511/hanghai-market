"""校园墙帖子的请求 / 响应结构。

匿名靠结构保证：PostOut 里没有任何投稿人字段，普通用户的接口只返回 PostOut；
只有管理员接口返回的 AdminPostOut 才带投稿人。
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PostStatus = Literal["pending", "online", "rejected", "offline"]

BODY_MIN, BODY_MAX, IMAGES_MAX = 2, 500, 4


class PostCreateIn(BaseModel):
    body: str = Field(description=f"正文，{BODY_MIN}–{BODY_MAX} 字")
    tag_id: int = Field(description="标签 id，来自 /api/meta/categories?type=post")
    images: list[str] = Field(default_factory=list, description=f"图片路径，最多 {IMAGES_MAX} 张，使用上传接口返回的 path")

    @field_validator("body")
    @classmethod
    def check_body(cls, v: str) -> str:
        v = v.strip()
        if not BODY_MIN <= len(v) <= BODY_MAX:
            raise ValueError(f"正文应为 {BODY_MIN}–{BODY_MAX} 个字")
        return v

    @field_validator("images")
    @classmethod
    def check_images(cls, v: list[str]) -> list[str]:
        if len(v) > IMAGES_MAX:
            raise ValueError(f"最多上传 {IMAGES_MAX} 张图片")
        for p in v:
            # 只接受本站上传接口返回的路径，防止塞外链或 ../ 路径穿越
            if not p.startswith("/uploads/") or ".." in p:
                raise ValueError("图片路径不合法，请使用上传接口返回的 path")
        return v


class OfficialPostIn(PostCreateIn):
    """管理员发布官方帖：不用审核，直接上墙。"""

    pinned: bool = Field(default=False, description="是否同时置顶")


class PostTag(BaseModel):
    id: int
    name: str
    slug: str


class PostOut(BaseModel):
    """一条帖子。注意：这里故意没有投稿人的任何信息（id、昵称、头像、学号都没有）。"""

    id: int
    body: str
    images: list[str] = Field(description="图片完整访问地址")
    tag: PostTag | None
    status: str
    is_mine: bool = Field(description="是不是当前登录用户自己投的（由服务器判断，只返回是 / 否）")
    is_official: bool = Field(description="管理员发布的官方帖")
    pinned: bool
    resolved: bool = Field(description="投稿人已标记「已解决」")
    like_count: int
    liked: bool = Field(default=False, description="当前登录用户是否点过赞")
    comment_count: int
    published_at: datetime | None = Field(description="上墙时间；未通过审核时为空")
    created_at: datetime | None = Field(description="投稿时间，仅投稿人本人和管理员可见")
    reject_reason: str | None = Field(description="退回原因，仅投稿人本人和管理员可见")


class TagCount(BaseModel):
    name: str
    slug: str
    count: int


class WallSummaryOut(BaseModel):
    """给没登录的人看的统计：只有数字，没有任何帖子内容。"""

    today: int = Field(description="今天（北京时间）新上墙的帖子数")
    total: int = Field(description="墙上的帖子总数")
    tags: list[TagCount] = Field(description="各标签下的帖子数")


class LikeOut(BaseModel):
    liked: bool
    like_count: int


COMMENT_MAX = 300


class CommentCreateIn(BaseModel):
    body: str = Field(description=f"评论内容，1–{COMMENT_MAX} 字")
    reply_to_id: int | None = Field(default=None, description="回复哪条评论；不填表示直接评论帖子")

    @field_validator("body")
    @classmethod
    def check_body(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= COMMENT_MAX:
            raise ValueError(f"评论应为 1–{COMMENT_MAX} 个字")
        return v


class CommentReplyTo(BaseModel):
    id: int
    name: str = Field(description="被回复者显示的名字：昵称，或者「楼主」")


class CommentOut(BaseModel):
    """一条评论。评论显示昵称；但投稿人在自己帖子下的评论显示为「楼主」，不带昵称（is_op=true, nickname=null）。"""

    id: int
    body: str
    nickname: str | None = Field(description="评论人昵称；楼主的评论为空")
    is_op: bool = Field(description="是不是楼主（帖子的投稿人）发的")
    is_mine: bool = Field(description="是不是当前登录用户发的")
    reply_to: CommentReplyTo | None
    created_at: datetime


class PostAuthor(BaseModel):
    id: int
    nickname: str
    student_no: str


class AdminPostOut(PostOut):
    """管理员审核时额外能看到：真实投稿人、AI 预审结果。"""

    author: PostAuthor
    ai_level: str | None = Field(description="AI 预审：ok 未发现问题 / attention 需要留意 / 空 未预审")
    ai_note: str | None
