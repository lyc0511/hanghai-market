"""认证接口：注册、登录、当前用户、修改密码。

业务错误码：
    40101 学号或密码错误    40102 账号已被封禁
    40103 原密码错误        40901 学号已注册
令牌缺失或失效时返回 HTTP 401（code 40100），由 deps.get_current_user 抛出。
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BizError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix="/auth", tags=["认证"])


def _token_for(user: User) -> TokenOut:
    token, expires_in = create_access_token(user.id)
    return TokenOut(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/register", response_model=ApiResponse[TokenOut], summary="注册（成功后直接登录）")
def register(body: RegisterIn, db: Session = Depends(get_db)) -> ApiResponse[TokenOut]:
    if db.scalar(select(User.id).where(User.student_no == body.student_no)) is not None:
        raise BizError(40901, "该学号已注册")
    user = User(
        student_no=body.student_no,
        nickname=body.nickname,
        password_hash=hash_password(body.password),
        campus_area=body.campus_area,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发注册同一学号时，唯一约束兜底
        db.rollback()
        raise BizError(40901, "该学号已注册")
    db.refresh(user)
    return ok(_token_for(user), "注册成功")


@router.post("/login", response_model=ApiResponse[TokenOut], summary="学号 + 密码登录")
def login(body: LoginIn, db: Session = Depends(get_db)) -> ApiResponse[TokenOut]:
    user = db.scalar(select(User).where(User.student_no == body.student_no))
    # 学号不存在和密码错误返回同一提示，避免被用来探测学号是否注册
    if user is None or not verify_password(body.password, user.password_hash):
        raise BizError(40101, "学号或密码错误")
    if user.status != "active":
        raise BizError(40102, "账号已被封禁")
    return ok(_token_for(user), "登录成功")


@router.get("/me", response_model=ApiResponse[UserOut], summary="当前登录用户")
def me(user: User = Depends(get_current_user)) -> ApiResponse[UserOut]:
    return ok(UserOut.model_validate(user))


@router.post("/password", response_model=ApiResponse[None], summary="修改密码")
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    if not verify_password(body.old_password, user.password_hash):
        raise BizError(40103, "原密码错误")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return ok(None, "密码已修改")
