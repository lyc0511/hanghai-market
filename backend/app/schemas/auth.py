import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 学号：纯数字；密码：8–32 位可见 ASCII 字符（bcrypt 最多处理 72 字节，限制 ASCII 可避免超长）
STUDENT_NO_RE = re.compile(r"\d{6,20}")
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
    campus_area: str | None = Field(default=None, max_length=32, description="所在校区")

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


class UserOut(BaseModel):
    """当前用户信息。不包含密码哈希和微信号密文。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    nickname: str
    avatar_url: str | None
    campus_area: str | None
    wechat_visible: bool
    role: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="有效期（秒）")
    user: UserOut
