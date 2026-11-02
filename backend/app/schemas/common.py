from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应外壳：{"code": 0, "message": "ok", "data": ...}"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class Page(BaseModel, Generic[T]):
    """分页外壳：items 为当前页数据，total 为符合条件的总条数。"""

    items: list[T]
    total: int
    page: int
    page_size: int


def ok(data: T | None = None, message: str = "ok") -> ApiResponse[T]:
    return ApiResponse(code=0, message=message, data=data)
