"""管理后台：物品审核、活动审核。所有接口都要求管理员身份。

状态流转：pending ──通过──▶ online
                 └─驳回──▶ rejected（附驳回原因）
只有 pending 的物品可以审核。每次审核在同一个事务里完成三件事：
改物品状态、给卖家发通知、写管理操作日志。

活动审核规则相同：只有 pending 的活动可以审核，通过后上架、驳回需填原因，并通知发布活动的会长。

业务错误码：
    40401 物品不存在    40902 物品当前状态不能审核
    40441 活动不存在    40943 活动当前状态不能审核
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.activities import load_activity, now_utc, page_of
from app.api.activities import to_detail as activity_detail
from app.api.deps import require_admin
from app.api.items import to_detail
from app.core.exceptions import BizError
from app.db.session import get_db
from app.models import Activity, AuditLog, Content, Notification, User
from app.schemas.activity import ActivityDetailOut
from app.schemas.admin import RejectIn
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.item import ItemDetailOut

router = APIRouter(prefix="/admin", tags=["管理后台"])

STATUS_LABELS = {"pending": "待审核", "online": "已上架", "offline": "已下架", "rejected": "已驳回", "deleted": "已删除"}


@router.get("/items", response_model=ApiResponse[Page[ItemDetailOut]], summary="物品审核列表")
def list_items_for_review(
    status: Literal["pending", "online", "rejected", "offline"] = Query(default="pending", description="按状态筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ItemDetailOut]]:
    where = (Content.type == "item", Content.status == status)
    total = db.scalar(select(func.count()).select_from(Content).where(*where))
    # 待审核按提交时间从早到晚，先来先审；其他状态按最新在前
    order = Content.created_at.asc() if status == "pending" else Content.created_at.desc()
    rows = db.scalars(
        select(Content)
        .where(*where)
        .options(joinedload(Content.item), joinedload(Content.owner), joinedload(Content.category))
        .order_by(order, Content.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ok(Page(items=[to_detail(c, admin) for c in rows], total=total, page=page, page_size=page_size))


def lock_pending_item(db: Session, item_id: int) -> Content:
    """取出物品并加行锁。两个管理员同时审核同一件时，后到的会等前一个提交，再看到最新状态。"""
    c = db.scalar(select(Content).where(Content.id == item_id, Content.type == "item").with_for_update())
    if c is None or c.status == "deleted":
        raise BizError(40401, "物品不存在")
    if c.status != "pending":
        raise BizError(40902, f"该物品当前状态为「{STATUS_LABELS.get(c.status, c.status)}」，不能审核")
    return c


def load_detail(db: Session, item_id: int, admin: User) -> ItemDetailOut:
    db.expire_all()  # 提交后重新读取，确保返回的是数据库里的最新数据
    c = db.scalar(
        select(Content)
        .where(Content.id == item_id)
        .options(joinedload(Content.item), joinedload(Content.owner), joinedload(Content.category))
    )
    return to_detail(c, admin)


@router.post("/items/{item_id}/approve", response_model=ApiResponse[ItemDetailOut], summary="审核通过（上架）")
def approve_item(
    item_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[ItemDetailOut]:
    c = lock_pending_item(db, item_id)
    c.status = "online"
    c.reject_reason = None
    db.add(Notification(
        user_id=c.owner_id,
        type="content_approved",
        title="物品审核已通过",
        body=f"你发布的「{c.title}」已通过审核，现已上架。",
        link=f"/items/{c.id}",
    ))
    db.add(AuditLog(admin_id=admin.id, action="approve_item", target_type="item", target_id=c.id))
    db.commit()
    return ok(load_detail(db, item_id, admin), "已通过，物品已上架")


@router.post("/items/{item_id}/reject", response_model=ApiResponse[ItemDetailOut], summary="审核驳回")
def reject_item(
    item_id: int,
    body: RejectIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[ItemDetailOut]:
    c = lock_pending_item(db, item_id)
    c.status = "rejected"
    c.reject_reason = body.reason
    db.add(Notification(
        user_id=c.owner_id,
        type="content_rejected",
        title="物品审核未通过",
        body=f"你发布的「{c.title}」未通过审核：{body.reason}",
        link=f"/items/{c.id}",
    ))
    db.add(AuditLog(
        admin_id=admin.id, action="reject_item", target_type="item", target_id=c.id, detail={"reason": body.reason}
    ))
    db.commit()
    return ok(load_detail(db, item_id, admin), "已驳回")


# ---------------------------------------------------------------- 活动审核

@router.get("/activities", response_model=ApiResponse[Page[ActivityDetailOut]], summary="活动审核列表")
def list_activities_for_review(
    status: Literal["pending", "online", "rejected"] = Query(default="pending", description="按状态筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ActivityDetailOut]]:
    stmt = (
        select(Content)
        .join(Activity, Activity.content_id == Content.id)
        .where(Content.type == "activity", Content.status == status)
    )
    # 待审核按提交时间先到先审；其他状态按活动开始时间，最近的在前
    order = (Content.created_at.asc(),) if status == "pending" else (Activity.start_time.desc(),)
    rows, total = page_of(db, stmt.order_by(*order, Content.id), page, page_size)
    return ok(Page(items=[activity_detail(db, c, admin) for c in rows], total=total, page=page, page_size=page_size))


def lock_pending_activity(db: Session, activity_id: int) -> Content:
    c = db.scalar(select(Content).where(Content.id == activity_id, Content.type == "activity").with_for_update())
    if c is None or c.status == "deleted":
        raise BizError(40441, "活动不存在")
    if c.status != "pending":
        raise BizError(40943, f"该活动当前状态为「{STATUS_LABELS.get(c.status, c.status)}」，不能审核")
    return c


@router.post("/activities/{activity_id}/approve", response_model=ApiResponse[ActivityDetailOut], summary="活动审核通过（上架）")
def approve_activity(
    activity_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[ActivityDetailOut]:
    c = lock_pending_activity(db, activity_id)
    note = ""
    if db.get(Activity, c.id).start_time <= now_utc():
        note = "（注意：活动开始时间已过，同学们无法报名）"
    c.status = "online"
    c.reject_reason = None
    db.add(Notification(
        user_id=c.owner_id, type="content_approved", title="活动审核已通过",
        body=f"你发布的活动「{c.title}」已通过审核，现在同学们可以报名了。", link=f"/activities/{c.id}",
    ))
    db.add(AuditLog(admin_id=admin.id, action="approve_activity", target_type="activity", target_id=c.id))
    db.commit()
    db.expire_all()
    return ok(activity_detail(db, load_activity(db, activity_id), admin), "已通过，活动已上架" + note)


@router.post("/activities/{activity_id}/reject", response_model=ApiResponse[ActivityDetailOut], summary="活动审核驳回")
def reject_activity(
    activity_id: int,
    body: RejectIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[ActivityDetailOut]:
    c = lock_pending_activity(db, activity_id)
    c.status = "rejected"
    c.reject_reason = body.reason
    db.add(Notification(
        user_id=c.owner_id, type="content_rejected", title="活动审核未通过",
        body=f"你发布的活动「{c.title}」未通过审核：{body.reason}", link=f"/activities/{c.id}",
    ))
    db.add(AuditLog(
        admin_id=admin.id, action="reject_activity", target_type="activity", target_id=c.id, detail={"reason": body.reason}
    ))
    db.commit()
    db.expire_all()
    return ok(activity_detail(db, load_activity(db, activity_id), admin), "已驳回")

