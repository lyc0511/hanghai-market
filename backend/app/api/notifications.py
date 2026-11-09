"""站内通知：查看、未读数、标为已读。

通知由各业务模块在状态变化时写入（交易意向、审核、入社申请、举报处理……），
统一通过本模块的 notify() 写，和业务数据在同一个事务里提交。

业务错误码：
    40461 通知不存在（或不是自己的）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BizError
from app.db.session import get_db
from app.models import Notification, User
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.notification import NotificationOut, UnreadCountOut

router = APIRouter(prefix="/notifications", tags=["通知"])


def notify(db: Session, user_id: int, ntype: str, title: str, body: str, link: str) -> None:
    """写一条通知。只 add 不 commit，由调用方和业务修改一起提交。"""
    db.add(Notification(user_id=user_id, type=ntype, title=title, body=body[:300], link=link))


def unread_count(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        or 0
    )


@router.get("", response_model=ApiResponse[Page[NotificationOut]], summary="我的通知（新的在前）")
def list_notifications(
    unread_only: bool = Query(default=False, description="true 只看未读"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[NotificationOut]]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [NotificationOut.model_validate(n) for n in rows]
    return ok(Page(items=items, total=int(total), page=page, page_size=page_size))


@router.get("/unread-count", response_model=ApiResponse[UnreadCountOut], summary="未读数量（顶部铃铛红点用）")
def get_unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[UnreadCountOut]:
    return ok(UnreadCountOut(count=unread_count(db, user.id)))


@router.post("/read-all", response_model=ApiResponse[UnreadCountOut], summary="全部标为已读")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[UnreadCountOut]:
    result = db.execute(
        update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)).values(is_read=True)
    )
    db.commit()
    return ok(UnreadCountOut(count=0), f"已将 {result.rowcount} 条通知标为已读")


@router.post("/{notification_id}/read", response_model=ApiResponse[UnreadCountOut], summary="标为已读，返回剩余未读数")
def read_one(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UnreadCountOut]:
    n = db.get(Notification, notification_id)
    # 别人的通知按「不存在」处理，不暴露它存在
    if n is None or n.user_id != user.id:
        raise BizError(40461, "通知不存在")
    n.is_read = True
    db.commit()
    return ok(UnreadCountOut(count=unread_count(db, user.id)))

