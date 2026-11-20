"""认证接口：注册、登录、当前用户、修改个人资料、修改密码。

业务错误码：
    40101 学号或密码错误    40102 账号已被封禁
    40103 原密码错误        40901 学号已注册
令牌缺失或失效时返回 HTTP 401（code 40100），由 deps.get_current_user 抛出。
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_user, get_current_user
from app.core.crypto import decrypt_text, encrypt_text
from app.core.exceptions import BizError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import ChangePasswordIn, LoginIn, ProfileUpdateIn, RegisterIn, TokenOut, UserOut
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix="/auth", tags=["认证"])


def user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.wechat_id = None if user.must_change_password else decrypt_text(user.wechat_id_enc)
    return out


def _token_for(user: User) -> TokenOut:
    token, expires_in = create_access_token(user.id, user.password_hash)
    return TokenOut(access_token=token, expires_in=expires_in, user=user_out(user))


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
def me(user: User = Depends(get_authenticated_user)) -> ApiResponse[UserOut]:
    return ok(user_out(user))


@router.patch("/me", response_model=ApiResponse[UserOut], summary="修改个人资料（含微信号）")
def update_me(
    body: ProfileUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserOut]:
    # exclude_unset：只处理前端实际传了的字段
    data = body.model_dump(exclude_unset=True)
    if data.get("nickname") is not None:
        user.nickname = data["nickname"]
    if data.get("campus_area") is not None:
        user.campus_area = data["campus_area"]
    if "avatar_url" in data:
        user.avatar_url = data["avatar_url"]
    if "wechat_id" in data:
        user.wechat_id_enc = encrypt_text(data["wechat_id"]) if data["wechat_id"] else None
    db.commit()
    return ok(user_out(user), "资料已更新")


@router.post("/password", response_model=ApiResponse[None], summary="修改密码")
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    if not verify_password(body.old_password, user.password_hash):
        raise BizError(40103, "原密码错误")
    if body.old_password == body.new_password:
        raise BizError(42200, "新密码不能与原密码相同")
    # 仅在密码仍是刚才核验的版本时更新，避免两个并发修改互相覆盖。
    changed_id = db.scalar(update(User).where(User.id == user.id, User.password_hash == user.password_hash)
                           .values(password_hash=hash_password(body.new_password), must_change_password=False).returning(User.id))
    if changed_id is None:
        raise BizError(40103, "密码已变更，请重新登录")
    db.commit()
    return ok(None, "密码已修改")
