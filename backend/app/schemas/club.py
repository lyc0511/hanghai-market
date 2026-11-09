"""社团目录、入社申请的请求和响应模型。"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import CampusArea

ClubType = Literal["academic", "art", "sports", "public", "other"]
RecruitStatus = Literal["recruiting", "closed"]
MyStatus = Literal["none", "pending", "member", "president"]
MemberRole = Literal["president", "member"]
ApplicationStatus = Literal["pending", "approved", "rejected"]


class ApplicationCreateIn(BaseModel):
    reason: str = Field(description="入社理由，1–300 字")

    @field_validator("reason")
    @classmethod
    def check_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("请填写入社理由")
        if len(v) > 300:
            raise ValueError("入社理由最多 300 个字")
        return v


class ApplicationRejectIn(BaseModel):
    note: str = Field(default="", max_length=200, description="拒绝说明，可不填，最多 200 字")

    @field_validator("note")
    @classmethod
    def strip_note(cls, v: str) -> str:
        return v.strip()


class ClubUpdateIn(BaseModel):
    """会长可改的资料：简介和招新信息。社团名称、会长本人不在这里改。"""

    summary: str = Field(description="社团简介，2–300 字")
    recruit_status: RecruitStatus = Field(description="recruiting 招新中 / closed 未招新")
    recruit_start: date | None = Field(default=None, description="招新开始日期")
    recruit_end: date | None = Field(default=None, description="招新结束日期")
    recruit_note: str = Field(default="", max_length=300, description="招新说明，最多 300 字")

    @field_validator("summary")
    @classmethod
    def check_summary(cls, v: str) -> str:
        v = v.strip()
        if not 2 <= len(v) <= 300:
            raise ValueError("简介应为 2–300 个字")
        return v

    @field_validator("recruit_note")
    @classmethod
    def strip_note(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def check_dates(self) -> "ClubUpdateIn":
        if self.recruit_status == "recruiting" and (self.recruit_start is None or self.recruit_end is None):
            raise ValueError("招新中需要填写开始和结束日期")
        if self.recruit_start is not None and self.recruit_end is not None and self.recruit_start > self.recruit_end:
            raise ValueError("招新开始日期不能晚于结束日期")
        return self


class UserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None = None


class ClubCardOut(BaseModel):
    """列表卡片。recruiting_now 表示「今天确实在招新」，比 recruit_status 多检查了起止日期。"""

    id: int
    title: str
    summary: str | None
    club_type: ClubType | str
    campus_area: CampusArea | str | None
    logo_url: str | None
    founded_year: int | None
    member_count: int
    recruit_status: str
    recruiting_now: bool
    president_nickname: str | None


class ClubDetailOut(ClubCardOut):
    tags: list[str]
    recruit_start: date | None
    recruit_end: date | None
    recruit_note: str | None
    president: UserBrief | None
    # 未登录为 null；登录后是 none / pending / member / president
    my_status: MyStatus | None
    # 只有会长能看到待审数量，其他人是 null
    pending_count: int | None = None
    created_at: datetime


class MyClubOut(ClubCardOut):
    my_role: MemberRole
    pending_count: int = 0


class MemberOut(BaseModel):
    user_id: int
    nickname: str
    avatar_url: str | None
    role: str
    joined_at: datetime


class ApplicationOut(BaseModel):
    id: int
    club_id: int
    user_id: int
    nickname: str
    avatar_url: str | None
    reason: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None


class MyApplicationOut(BaseModel):
    id: int
    club_id: int
    club_title: str
    reason: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None
