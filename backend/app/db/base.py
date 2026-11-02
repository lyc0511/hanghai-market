from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类（SQLAlchemy 2.x 写法）。"""


def utcnow() -> datetime:
    """统一的 UTC 当前时间（带时区），用于 ORM 端的 onupdate。"""
    return datetime.now(timezone.utc)
