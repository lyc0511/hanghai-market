"""通用路由依赖：当前登录用户、管理员校验。

用法：
    def handler(user: User = Depends(get_current_user)): ...
    def handler(admin: User = Depends(require_admin)): ...
    def handler(user: User | None = Depends(get_optional_user)): ...   # 游客也能访问
"""
from hmac import compare_digest

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, session_stamp
from app.db.session import get_db
from app.models import User

# auto_error=False：缺少 Authorization 头时由我们自己抛 401，保证错误格式统一
bearer_scheme = HTTPBearer(auto_error=False, description="登录接口返回的 access_token")


def session_user(db: Session, token: str) -> User | None:
    claims = decode_access_token(token)
    if claims is None:
        return None
    user_id, stamp = claims
    user = db.get(User, user_id)
    if user is None or not compare_digest(stamp, session_stamp(user.password_hash)):
        return None
    return user


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status_code=401, detail="请先登录")
    user = session_user(db, cred.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被封禁")
    return user


def get_optional_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """可选登录：未带令牌、令牌无效或账号被封时都按游客处理，不报错。"""
    if cred is None:
        return None
    user = session_user(db, cred.credentials)
    return user if user is not None and user.status == "active" else None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
