"""社团活动、报名的请求和响应模型。"""
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

Phase = Literal["upcoming", "ongoing", "ended"]
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def _aware(v: datetime | None) -> datetime | None:
    """前端没带时区时按北京时间理解，统一转成带时区的时间再比较。"""
    if v is not None and v.tzinfo is None:
        return v.replace(tzinfo=LOCAL_TZ)
    return v


class ActivityCreateIn(BaseModel):
    title: str = Field(description="活动名称，2–60 字")
    summary: str = Field(default="", max_length=300, description="活动介绍，最多 300 字")
    location: str = Field(description="活动地点，1–128 字")
    start_time: datetime = Field(description="开始时间")
    end_time: datetime = Field(description="结束时间")
    signup_deadline: datetime | None = Field(default=None, description="报名截止时间，不填默认等于开始时间")
    capacity: int = Field(ge=1, le=1000, description="名额，1–1000")
    tags: list[str] = Field(default_factory=list, description="标签，最多 5 个，每个最多 10 字")

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        v = v.strip()
        if not 2 <= len(v) <= 60:
            raise ValueError("活动名称应为 2–60 个字")
        return v

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, v: str) -> str:
        return v.strip()

    @field_validator("location")
    @classmethod
    def check_location(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 128:
            raise ValueError("请填写活动地点，最多 128 字")
        return v

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v: list[str]) -> list[str]:
        tags = list(dict.fromkeys(t.strip() for t in v if t.strip()))
        if len(tags) > 5 or any(len(t) > 10 for t in tags):
            raise ValueError("标签最多 5 个，每个最多 10 字")
        return tags

    @field_validator("start_time", "end_time", "signup_deadline")
    @classmethod
    def to_aware(cls, v: datetime | None) -> datetime | None:
        return _aware(v)

    @model_validator(mode="after")
    def check_times(self) -> "ActivityCreateIn":
        now = datetime.now(LOCAL_TZ)
        if self.start_time <= now:
            raise ValueError("开始时间必须晚于现在")
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        if self.signup_deadline is not None:
            if self.signup_deadline <= now:
                raise ValueError("报名截止时间必须晚于现在")
            if self.signup_deadline > self.start_time:
                raise ValueError("报名截止时间不能晚于开始时间")
        return self


class ClubBrief(BaseModel):
    id: int
    title: str


class ActivityCardOut(BaseModel):
    """列表里的一行。phase 是按当前时间算出来的阶段；signup_open 表示此刻能不能报名。"""

    id: int
    title: str
    summary: str | None
    club: ClubBrief
    campus_area: str | None
    location: str
    start_time: datetime
    end_time: datetime
    signup_deadline: datetime | None
    capacity: int
    enrolled_count: int
    phase: Phase
    signup_open: bool
    status: str
    tags: list[str]


class ActivityDetailOut(ActivityCardOut):
    view_count: int
    # 未登录为 null；登录后表示我是否已报名
    signed_up: bool | None
    # 是否是主办社团的会长（可查看报名名单）
    is_organizer: bool
    reject_reason: str | None = Field(description="驳回原因，只有会长和管理员能看到")
    created_at: datetime


class MyActivityOut(ActivityCardOut):
    signed_at: datetime


class SignupOut(BaseModel):
    user_id: int
    nickname: str
    avatar_url: str | None
    signed_at: datetime
