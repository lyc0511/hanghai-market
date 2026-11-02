"""业务异常与全局异常处理器。

所有错误响应统一为 {"code": int, "message": str, "data": null}。
错误码约定：40000 参数错误 / 40400 资源不存在 / 4xx00 其他 HTTP 错误 / 50000 服务器内部错误。
"""
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("campus")


class BizError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: int, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": None},
    )


async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    # 业务错误统一返回 HTTP 200，由前端根据 code 判断
    return _error(exc.code, exc.message, 200)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x not in ("query", "body", "path"))
    # 自定义校验器抛出的 ValueError 会被 Pydantic 加上 "Value error, " 前缀，去掉后只保留中文提示
    detail = str(first.get("msg", "")).removeprefix("Value error, ")
    msg = f"参数错误：{loc} {detail}".strip()
    return _error(40000, msg, 422)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error(exc.status_code * 100, str(exc.detail), exc.status_code)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("未捕获异常 %s %s\n%s", request.method, request.url.path, traceback.format_exc())
    return _error(50000, "服务器内部错误", 500)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BizError, biz_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
