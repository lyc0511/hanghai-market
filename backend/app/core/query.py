"""查询小工具：模糊搜索转义、分页。各业务模块共用，避免每个文件各写一份。"""
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def escape_like(s: str) -> str:
    """转义 LIKE 通配符，让用户输入的 % 和 _ 按普通字符匹配（配合 escape="\\\\" 使用）。"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def contains(s: str) -> str:
    """生成「包含 s」的 LIKE 模式：%s%（已转义）。"""
    return f"%{escape_like(s)}%"


def count_rows(db: Session, stmt: Select) -> int:
    """统计一个查询的总行数（去掉排序再套一层子查询计数）。"""
    return int(db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)


def paginate(
    db: Session,
    stmt: Select,
    page: int,
    page_size: int,
    *,
    options: Sequence[Any] = (),
    scalars: bool = True,
) -> tuple[list[Any], int]:
    """分页查询，返回 (当前页数据, 总条数)。

    options：取数据时附加的预加载（joinedload 等），计数时不带，避免多余的 JOIN；
    scalars：True 返回 ORM 对象列表；查询多列时传 False，返回 Row 列表。
    """
    total = count_rows(db, stmt)
    q = stmt.options(*options).offset((page - 1) * page_size).limit(page_size)
    rows = db.scalars(q).all() if scalars else db.execute(q).all()
    return list(rows), total
