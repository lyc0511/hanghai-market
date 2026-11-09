"""举报相关的请求 / 响应结构。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TargetType = Literal["item", "club", "activity"]
Reason = Literal["fraud", "prohibited", "false_info", "spam", "abuse", "other"]
ReportStatus = Literal["pending", "resolved", "dismissed"]


class ReportCreateIn(BaseModel):
    target_type: TargetType
    target_id: int = Field(gt=0)
    reason: Reason
    description: str | None = Field(default=None, max_length=300, description="补充说明，选「其他」时必填")


class ReportTarget(BaseModel):
    type: TargetType
    id: int
    title: str
    status: str
    link: str


class UserMini(BaseModel):
    id: int
    nickname: str
    student_no: str | None = None


class ReportOut(BaseModel):
    """举报人在「我的举报」里看到的内容。"""

    id: int
    target: ReportTarget
    reason: Reason
    description: str | None
    status: ReportStatus
    handle_note: str | None
    created_at: datetime


class AdminReportOut(ReportOut):
    """管理员额外能看到：举报人、被举报内容的发布者、处理人、同一内容被举报的次数。"""

    reporter: UserMini
    owner: UserMini
    handler: UserMini | None
    same_target_pending: int = Field(description="同一内容当前待处理的举报数（含本条）")


class ReportHandleIn(BaseModel):
    action: Literal["resolve", "dismiss"] = Field(description="resolve 举报属实 / dismiss 驳回举报")
    note: str = Field(min_length=1, max_length=300, description="处理说明，会通知举报人")
    takedown: bool = Field(default=False, description="举报属实时是否同时下架被举报内容")
