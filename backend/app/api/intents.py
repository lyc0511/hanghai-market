"""交易意向：买家发起 → 卖家接受 / 拒绝 → 双方互看微信 → 卖家标记成交。

状态流转：
    pending ──卖家接受──▶ accepted ──卖家标记成交──▶ completed（物品自动下架）
       │  └─卖家拒绝──▶ rejected
       └──────┴─买家取消──▶ cancelled
卖家可以同时接受多个意向；某一单成交后，同一物品其余进行中的意向自动关闭并通知买家。

业务错误码：
    40402 意向不存在               40301 无权操作该意向
    40903 已对该物品发起过意向       40904 意向当前状态不能执行此操作
    42202 需要先填写微信号           42203 不能对自己的物品发起意向
    42204 物品不在售
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.notifications import notify
from app.api.upload import public_url
from app.core.crypto import decrypt_text
from app.core.exceptions import BizError
from app.db.session import get_db
from app.models import Content, Item, TradeIntent, User
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.intent import IntentCreateIn, IntentItemBrief, IntentOut, UserBrief

router = APIRouter(prefix="/intents", tags=["交易意向"])

STATUS_LABELS = {"pending": "待处理", "accepted": "已接受", "rejected": "已拒绝", "completed": "已成交", "cancelled": "已取消"}
ACTIVE = ("pending", "accepted")


def to_out(t: TradeIntent, viewer: User) -> IntentOut:
    i_am_buyer = viewer.id == t.buyer_id
    other = t.seller if i_am_buyer else t.buyer
    content = t.item.content
    # 只有卖家接受之后，双方才能看到对方的微信号
    wechat = decrypt_text(other.wechat_id_enc) if t.status in ("accepted", "completed") else None
    return IntentOut(
        id=t.id,
        status=t.status,
        my_role="buyer" if i_am_buyer else "seller",
        message=t.message,
        item=IntentItemBrief(
            id=content.id,
            title=content.title,
            price=float(t.item.price),
            cover=public_url(t.item.images[0]) if t.item.images else None,
            status=content.status,
        ),
        counterpart=UserBrief(id=other.id, nickname=other.nickname, avatar_url=other.avatar_url),
        counterpart_wechat=wechat,
        contact_revealed_at=t.contact_revealed_at,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def load_intent(db: Session, intent_id: int) -> TradeIntent | None:
    return db.scalar(
        select(TradeIntent)
        .where(TradeIntent.id == intent_id)
        .options(
            joinedload(TradeIntent.item).joinedload(Item.content),
            joinedload(TradeIntent.buyer),
            joinedload(TradeIntent.seller),
        )
    )


def lock_intent(db: Session, intent_id: int, user: User, role: Literal["buyer", "seller"], allowed: tuple[str, ...]) -> TradeIntent:
    """先锁所属物品，再读取并锁定意向，与下架和批量关闭操作顺序一致。"""
    item_id = select(TradeIntent.item_id).where(TradeIntent.id == intent_id).scalar_subquery()
    db.scalar(select(Content.id).where(Content.id == item_id).with_for_update())
    t = db.scalar(select(TradeIntent).where(TradeIntent.id == intent_id).with_for_update())
    if t is None:
        raise BizError(40402, "意向不存在")
    owner_id = t.buyer_id if role == "buyer" else t.seller_id
    if owner_id != user.id:
        raise BizError(40301, "无权操作该意向")
    if t.status not in allowed:
        raise BizError(40904, f"该意向当前状态为「{STATUS_LABELS.get(t.status, t.status)}」，不能执行此操作")
    return t


def fresh(db: Session, intent_id: int, user: User) -> IntentOut:
    db.expire_all()
    return to_out(load_intent(db, intent_id), user)


@router.post("", response_model=ApiResponse[IntentOut], summary="发起交易意向（买家）")
def create_intent(
    body: IntentCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[IntentOut]:
    content = db.scalar(select(Content).where(Content.id == body.item_id, Content.type == "item").with_for_update())
    if content is None or content.status != "online":
        raise BizError(42204, "物品不存在或已下架")
    if content.owner_id == user.id:
        raise BizError(42203, "不能对自己的物品发起意向")
    if not user.wechat_id_enc:
        raise BizError(42202, "请先在个人资料中填写微信号，卖家接受后会展示给对方")

    exists = db.scalar(
        select(TradeIntent.id).where(
            TradeIntent.item_id == content.id,
            TradeIntent.buyer_id == user.id,
            TradeIntent.status.in_(("pending", "accepted", "completed")),
        )
    )
    if exists is not None:
        raise BizError(40903, "你已对该物品发起过意向，可在「我的意向」中查看")

    t = TradeIntent(item_id=content.id, buyer_id=user.id, seller_id=content.owner_id, message=body.message or None)
    db.add(t)
    notify(
        db, content.owner_id, "intent_new", "收到新的购买意向",
        f"{user.nickname} 对你的「{content.title}」发起了购买意向" + (f"：{body.message}" if body.message else "。"),
        f"/items/{content.id}",
    )
    try:
        db.commit()
    except IntegrityError:
        # 同一买家并发重复提交时，数据库的部分唯一索引兜底
        db.rollback()
        raise BizError(40903, "你已对该物品发起过意向，可在「我的意向」中查看")
    return ok(fresh(db, t.id, user), "已发起意向，等待卖家处理")


@router.get("/mine", response_model=ApiResponse[Page[IntentOut]], summary="我的意向（我买的 / 我卖的）")
def list_my_intents(
    role: Literal["buyer", "seller"] | None = Query(default=None, description="buyer 我发起的 / seller 我收到的；不传返回全部"),
    status: Literal["pending", "accepted", "rejected", "completed", "cancelled"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[IntentOut]]:
    if role == "buyer":
        cond = TradeIntent.buyer_id == user.id
    elif role == "seller":
        cond = TradeIntent.seller_id == user.id
    else:
        cond = or_(TradeIntent.buyer_id == user.id, TradeIntent.seller_id == user.id)
    stmt = select(TradeIntent).where(cond)
    if status is not None:
        stmt = stmt.where(TradeIntent.status == status)

    total =db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.options(
            joinedload(TradeIntent.item).joinedload(Item.content),
            joinedload(TradeIntent.buyer),
            joinedload(TradeIntent.seller),
        )
        .order_by(TradeIntent.updated_at.desc(), TradeIntent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ok(Page(items=[to_out(t, user) for t in rows], total=total, page=page, page_size=page_size))


@router.post("/{intent_id}/accept", response_model=ApiResponse[IntentOut], summary="接受意向（卖家），双方可见微信号")
def accept_intent(intent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[IntentOut]:
    t = lock_intent(db, intent_id, user, "seller", ("pending",))
    if not user.wechat_id_enc:
        raise BizError(42202, "请先在个人资料中填写微信号，接受后会展示给买家")
    content = db.get(Content, t.item_id)
    if content.status != "online":
        raise BizError(42204, "物品已下架，不能接受意向")
    t.status = "accepted"
    t.contact_revealed_at = datetime.now(timezone.utc)
    notify(
        db, t.buyer_id, "intent_accepted", "卖家已接受你的意向",
        f"卖家已同意交易「{content.title}」，可在「我的意向」中查看对方微信号。", "/me/intents",
    )
    db.commit()
    return ok(fresh(db, intent_id, user), "已接受，双方现在可以看到对方的微信号")


@router.post("/{intent_id}/reject", response_model=ApiResponse[IntentOut], summary="拒绝意向（卖家）")
def reject_intent(intent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[IntentOut]:
    t = lock_intent(db, intent_id, user, "seller", ("pending",))
    content = db.get(Content, t.item_id)
    t.status = "rejected"
    notify(db, t.buyer_id, "intent_rejected", "卖家未接受你的意向", f"卖家暂时不考虑「{content.title}」的这次交易。", "/me/intents")
    db.commit()
    return ok(fresh(db, intent_id, user), "已拒绝")


@router.post("/{intent_id}/cancel", response_model=ApiResponse[IntentOut], summary="取消意向（买家）")
def cancel_intent(intent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[IntentOut]:
    t = lock_intent(db, intent_id, user, "buyer", ACTIVE)
    content = db.get(Content, t.item_id)
    t.status = "cancelled"
    notify(db, t.seller_id, "intent_cancelled", "买家取消了意向", f"{user.nickname} 取消了对「{content.title}」的购买意向。", f"/items/{content.id}")
    db.commit()
    return ok(fresh(db, intent_id, user), "已取消")


@router.post("/{intent_id}/complete", response_model=ApiResponse[IntentOut], summary="标记成交（卖家），物品自动下架")
def complete_intent(intent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[IntentOut]:
    t = lock_intent(db, intent_id, user, "seller", ("accepted",))
    content = db.get(Content, t.item_id)
    if content.status != "online":
        raise BizError(42204, "物品已下架或已售出")
    now = datetime.now(timezone.utc)
    t.status = "completed"
    content.status = "offline"
    db.get(Item, content.id).sold_at = now
    notify(db, t.buyer_id, "intent_completed", "交易已完成", f"「{content.title}」已成交，感谢使用。", "/me/intents")

    # 同一物品其余进行中的意向自动关闭
    others = db.scalars(
        select(TradeIntent).where(
            TradeIntent.item_id == content.id, TradeIntent.id != t.id, TradeIntent.status.in_(ACTIVE)
        )
    ).all()
    for o in others:
        o.status = "rejected"
        notify(db, o.buyer_id, "intent_closed", "物品已售出", f"你想要的「{content.title}」已经卖给其他同学了。", "/me/intents")
    db.commit()
    msg = "已标记成交，物品已下架" + (f"，另有 {len(others)} 个意向已自动关闭" if others else "")
    return ok(fresh(db, intent_id, user), msg)
