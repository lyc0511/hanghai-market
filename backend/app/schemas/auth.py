import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import CampusArea

# 学号：纯数字；密码：8–32 位可见 ASCII 字符（bcrypt 最多处理 72 字节，限制 ASCII 可避免超长）
STUDENT_NO_RE = re.compile(r"\d{6,20}")
# 微信号：字母开头 6–20 位（字母、数字、下划线、减号），或 11 位手机号（微信也支持用手机号搜索）
WECHAT_RE = re.compile(r"[a-zA-Z][-_a-zA-Z0-9]{5,19}|1\d{10}")
PASSWORD_RE = re.compile(r"[\x21-\x7E]{8,32}")


def _check_student_no(v: str) -> str:
    if not STUDENT_NO_RE.fullmatch(v):
        raise ValueError("学号应为 6–20 位数字")
    return v


def _check_password(v: str) -> str:
    if not PASSWORD_RE.fullmatch(v):
        raise ValueError("密码应为 8–32 位，不能含空格或中文")
    if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
        raise ValueError("密码必须同时包含字母和数字")
    return v


class RegisterIn(BaseModel):
    student_no: str = Field(description="学号，6–20 位数字")
    nickname: str = Field(min_length=1, max_length=30, description="昵称")
    password: str = Field(description="8–32 位，需同时包含字母和数字")
    campus_area: CampusArea | None = Field(default=None, description="所在校区")

    @field_validator("nickname")
    @classmethod
    def strip_nickname(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("昵称不能为空")
        return v

    _student_no = field_validator("student_no")(_check_student_no)
    _password = field_validator("password")(_check_password)


class LoginIn(BaseModel):
    student_no: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=72)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(description="8–32 位，需同时包含字母和数字")

    _password = field_validator("new_password")(_check_password)


class ProfileUpdateIn(BaseModel):
    """修改个人资料：只传要改的字段，不传的保持不变。"""

    nickname: str | None = Field(default=None, min_length=1, max_length=30)
    campus_area: CampusArea | None = None
    avatar_url: str | None = Field(default=None, description="头像，使用上传接口返回的 path")
    wechat_id: str | None = Field(default=None, description="微信号，加密存储；传空字符串表示清除")

    @field_validator("nickname")
    @classmethod
    def strip_nickname(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("昵称不能为空")
        return v

    @field_validator("avatar_url")
    @classmethod
    def check_avatar(cls, v: str | None) -> str | None:
        if v is not None and (not v.startswith("/uploads/") or ".." in v):
            raise ValueError("头像路径不合法，请使用上传接口返回的 path")
        return v

    @field_validator("wechat_id")
    @classmethod
    def check_wechat(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if v and not WECHAT_RE.fullmatch(v):
            raise ValueError("微信号格式不正确：应为字母开头的 6–20 位字母数字，或 11 位手机号")
        return v


class UserOut(BaseModel):
    """当前用户自己的信息。不包含密码哈希；微信号是解密后的明文，只返回给本人。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    nickname: str
    avatar_url: str | None
    campus_area: str | None
    wechat_visible: bool
    role: str
    wechat_id: str | None = Field(default=None, description="本人的微信号（已解密）")
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="有效期（秒）")
    user: UserOut
