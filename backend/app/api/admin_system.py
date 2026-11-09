"""管理后台：数据看板、用户管理（封禁 / 解封）、操作日志。所有接口都要求管理员身份。

封禁：
    - 被封禁的账号立即失效：登录接口拒绝，已登录的令牌在下一次请求时也会被拦下（deps.get_current_user 每次查库）；
    - 可选「同时下架其在售物品」，防止买家继续对联系不上的卖家发起意向；
      解封时不会自动重新上架，由同学自己在「我发布的」里重新上架；
    - 不能封禁自己，也不能封禁其他管理员。

业务错误码：
    40471 用户不存在    40371 不能封禁管理员或自己    40971 用户当前状态不能执行此操作
"""
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.notifications import notify
from app.core.exceptions import BizError
from app.core.query import contains
from app.db.session import get_db
from app.models import (
    Activity,
    ActivitySignup,
    AuditLog,
    Club,
    ClubApplication,
    Content,
    Item,
    Report,
    TradeIntent,
    User,
)
from app.schemas.admin_system import AdminUserOut, AuditLogOut, BanIn, DashboardOut, DayCount
from app.schemas.common import ApiResponse, Page, ok

router = APIRouter(prefix="/admin", tags=["管理后台"])

BJ = ZoneInfo("Asia/Shanghai")


def count(db: Session, model, *where) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*where)) or 0)


def per_day(db: Session, column, since: datetime, *where) -> dict[date, int]:
    """按北京时间的日期分组计数。"""
    day = cast(func.timezone("Asia/Shanghai", column), Date)
    rows = db.execute(select(day, func.count()).where(column >= since, *where).group_by(day)).all()
    return {d: n for d, n in rows}


# ---------------------------------------------------------------- 数据看板

@router.get("/dashboard", response_model=ApiResponse[DashboardOut], summary="数据看板")
def dashboard(
    days: int = Query(default=30, ge=7, le=90, description="趋势图统计最近多少天"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[DashboardOut]:
    now = datetime.now(timezone.utc)
    today = now.astimezone(BJ).date()
    # 趋势：从 (days-1) 天前的北京时间 0 点开始，每天一个点，没数据的日子补 0
    start_day = today - timedelta(days=days - 1)
    since = datetime.combine(start_day, datetime.min.time(), tzinfo=BJ)
    week_ago = datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=BJ)

    new_users = per_day(db, User.created_at, since)
    new_items = per_day(db, Content.created_at, since, Content.type == "item")
    new_intents = per_day(db, TradeIntent.created_at, since)
    trend = [
        DayCount(day=d, users=new_users.get(d, 0), items=new_items.get(d, 0), intents=new_intents.get(d, 0))
        for d in (start_day + timedelta(days=i) for i in range(days))
    ]

    item_online = (Content.type == "item", Content.status == "online")
    return ok(DashboardOut(
        users_total=count(db, User),
        users_new_7d=count(db, User, User.created_at >= week_ago),
        users_banned=count(db, User, User.status == "banned"),
        items_online=count(db, Content, *item_online),
        items_sold=count(db, Item, Item.sold_at.is_not(None)),
        clubs_total=count(db, Content, Content.type == "club", Content.status == "online"),
        clubs_recruiting=int(db.scalar(
            select(func.count()).select_from(Club).join(Content, Content.id == Club.content_id).where(
                Content.status == "online", Club.recruit_status == "recruiting",
                Club.recruit_start <= today, Club.recruit_end >= today,
            )
        ) or 0),
        activities_upcoming=int(db.scalar(
            select(func.count()).select_from(Activity).join(Content, Content.id == Activity.content_id).where(
                Content.status == "online", Activity.start_time > now,
            )
        ) or 0),
        signups_total=count(db, ActivitySignup, ActivitySignup.status == "signed"),
        intents_total=count(db, TradeIntent),
        intents_completed=count(db, TradeIntent, TradeIntent.status == "completed"),
        todo_items=count(db, Content, Content.type == "item", Content.status == "pending"),
        todo_activities=count(db, Content, Content.type == "activity", Content.status == "pending"),
        todo_reports=count(db, Report, Report.status == "pending"),
        todo_clubs=count(db, ClubApplication, ClubApplication.status == "pending"),
        trend=trend,
    ))


# ---------------------------------------------------------------- 用户管理

def user_out(db: Session, u: User) -> AdminUserOut:
    reported = db.scalar(
        select(func.count()).select_from(Report).join(Content, Content.id == Report.target_id).where(Content.owner_id == u.id)
    )
    return AdminUserOut(
        id=u.id, student_no=u.student_no, nickname=u.nickname, campus_area=u.campus_area,
        role=u.role, status=u.status, created_at=u.created_at,
        items_count=count(db, Content, Content.owner_id == u.id, Content.type == "item", Content.status != "deleted"),
        intents_count=count(db, TradeIntent, or_(TradeIntent.buyer_id == u.id, TradeIntent.seller_id == u.id)),
        reported_count=int(reported or 0),
    )


@router.get("/users", response_model=ApiResponse[Page[AdminUserOut]], summary="用户列表（按学号 / 昵称搜索）")
def list_users(
    keyword: str | None = Query(default=None, max_length=30),
    status: Literal["active", "banned"] | None = Query(default=None),
    role: Literal["student", "admin"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[AdminUserOut]]:
    where = []
    if keyword and keyword.strip():
        k = contains(keyword.strip())
        where.append(or_(User.student_no.like(k, escape="\\"), User.nickname.ilike(k, escape="\\")))
    if status:
        where.append(User.status == status)
    if role:
        where.append(User.role == role)
    total = count(db, User, *where)
    rows = db.scalars(
        select(User).where(*where).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ok(Page(items=[user_out(db, u) for u in rows], total=total, page=page, page_size=page_size))


def lock_user(db: Session, user_id: int, admin: User) -> User:
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if u is None:
        raise BizError(40471, "用户不存在")
    if u.id == admin.id or u.role == "admin":
        raise BizError(40371, "不能封禁管理员账号或自己")
    return u


@router.post("/users/{user_id}/ban", response_model=ApiResponse[AdminUserOut], summary="封禁用户")
def ban_user(
    user_id: int,
    body: BanIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminUserOut]:
    u = lock_user(db, user_id, admin)
    if u.status != "active":
        raise BizError(40971, "该用户已经是封禁状态")
    reason = body.reason.strip()
    u.status = "banned"

    offlined: list[int] = []
    if body.offline_items:
        items = db.scalars(
            select(Content).where(Content.owner_id == u.id, Content.type == "item", Content.status == "online").with_for_update()
        ).all()
        for c in items:
            c.status = "offline"
            offlined.append(c.id)
    # 被封禁的人暂时看不到通知，但解封后能看到原因
    notify(db, u.id, "account_banned", "账号已被封禁", f"你的账号因「{reason}」被封禁，如有疑问请联系管理员。", "/me")
    db.add(AuditLog(
        admin_id=admin.id, action="ban_user", target_type="user", target_id=u.id,
        detail={"reason": reason, "offline_items": offlined},
    ))
    db.commit()
    db.refresh(u)
    msg = "已封禁" + (f"，下架了 {len(offlined)} 件在售物品" if offlined else "")
    return ok(user_out(db, u), msg)


@router.post("/users/{user_id}/unban", response_model=ApiResponse[AdminUserOut], summary="解除封禁")
def unban_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> ApiResponse[AdminUserOut]:
    u = lock_user(db, user_id, admin)
    if u.status != "banned":
        raise BizError(40971, "该用户没有被封禁")
    u.status = "active"
    notify(db, u.id, "account_unbanned", "账号已解除封禁", "你的账号已恢复正常。之前被下架的物品可以在「我发布的」里重新上架。", "/me/items")
    db.add(AuditLog(admin_id=admin.id, action="unban_user", target_type="user", target_id=u.id))
    db.commit()
    db.refresh(u)
    return ok(user_out(db, u), "已解除封禁")


# ---------------------------------------------------------------- 操作日志

@router.get("/audit-logs", response_model=ApiResponse[Page[AuditLogOut]], summary="管理操作日志")
def list_audit_logs(
    action: str | None = Query(default=None, max_length=64, description="按操作类型筛选，如 approve_item"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[AuditLogOut]]:
    where = [AuditLog.action == action] if action else []
    total = count(db, AuditLog, *where)
    rows = db.execute(
        select(AuditLog, User.nickname)
        .join(User, User.id == AuditLog.admin_id)
        .where(*where)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        AuditLogOut(
            id=a.id, admin_id=a.admin_id, admin_nickname=nick, action=a.action, target_type=a.target_type,
            target_id=a.target_id, detail=a.detail, created_at=a.created_at,
        )
        for a, nick in rows
    ]
    return ok(Page(items=items, total=total, page=page, page_size=page_size))
