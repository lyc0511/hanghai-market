"""管理后台：数据看板、用户管理、操作日志。"""
from datetime import date, datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field


class DayCount(BaseModel):
    day: date
    users: int
    items: int
    intents: int


class DashboardOut(BaseModel):
    users_total: int
    users_new_7d: int
    users_banned: int
    items_online: int
    items_sold: int
    clubs_total: int
    clubs_recruiting: int
    activities_upcoming: int
    signups_total: int
    intents_total: int
    intents_completed: int
    todo_items: int = Field(description="待审核物品")
    todo_activities: int = Field(description="待审核活动")
    todo_posts: int = Field(description="待审核的校园墙投稿")
    todo_reports: int = Field(description="待处理举报")
    todo_clubs: int = Field(description="待审核入社申请（由会长处理，这里只展示）")
    trend: list[DayCount] = Field(description="最近 N 天（北京时间）每天新增")


class AdminUserOut(BaseModel):
    id: int
    student_no: str
    nickname: str
    campus_area: str | None
    role: str
    status: str
    created_at: datetime
    items_count: int
    intents_count: int
    reported_count: int = Field(description="名下内容被举报次数")


class BanIn(BaseModel):
    reason: str = Field(min_length=2, max_length=200)
    offline_items: bool = Field(default=True, description="同时下架其在售物品")


class PasswordResetIn(BaseModel):
    identity_verified: Literal[True]


class PasswordResetOut(BaseModel):
    temporary_password: str


class AuditLogOut(BaseModel):
    id: int
    admin_id: int
    admin_nickname: str
    action: str
    target_type: str | None
    target_id: int | None
    detail: dict[str, Any] | None
    created_at: datetime
