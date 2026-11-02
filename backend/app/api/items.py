"""二手物品：发布、详情。

发布后状态为 pending（待审核），管理员审核通过后变为 online 才对其他人可见。

业务错误码：
    40401 物品不存在                42201 类目不存在或不是物品类目
    42901 今日发布数量已达上限
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_optional_user
from app.api.upload import public_url
from app.core.config import settings
from app.core.exceptions import BizError
from app.db.session import get_db
from app.models import Category, Content, Item, User
from app.schemas.common import ApiResponse, ok
from app.schemas.item import CategoryBrief, ItemCreateIn, ItemDetailOut, SellerBrief

router = APIRouter(prefix="/items", tags=["二手物品"])

# 「每天」按北京时间零点切分，而不是 UTC
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def build_search_text(title: str, summary: str | None, tags: list[str]) -> str:
    """拼接搜索用文本，规则与 scripts/seed.py 保持一致。"""
    return " ".join([title, summary or "", *tags])


def to_detail(c: Content, viewer: User | None) -> ItemDetailOut:
    is_mine = viewer is not None and viewer.id == c.owner_id
    can_see_private = is_mine or (viewer is not None and viewer.role == "admin")
    return ItemDetailOut(
        id=c.id,
        title=c.title,
        summary=c.summary,
        category=CategoryBrief(id=c.category.id, name=c.category.name) if c.category else None,
        tags=c.tags,
        campus_area=c.campus_area,
        status=c.status,
        reject_reason=c.reject_reason if can_see_private else None,
        view_count=c.view_count,
        price=float(c.item.price),
        original_price=float(c.item.original_price) if c.item.original_price is not None else None,
        condition=c.item.condition,
        images=[public_url(p) for p in c.item.images],
        sold_at=c.item.sold_at,
        seller=SellerBrief(
            id=c.owner.id, nickname=c.owner.nickname, avatar_url=c.owner.avatar_url, campus_area=c.owner.campus_area
        ),
        is_mine=is_mine,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def load_item(db: Session, content_id: int) -> Content | None:
    stmt = (
        select(Content)
        .where(Content.id == content_id, Content.type == "item")
        .options(joinedload(Content.item), joinedload(Content.owner), joinedload(Content.category))
    )
    return db.scalar(stmt)


@router.post("", response_model=ApiResponse[ItemDetailOut], summary="发布物品（提交后待审核）")
def create_item(
    body: ItemCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ItemDetailOut]:
    category = db.get(Category, body.category_id)
    if category is None or category.type != "item":
        raise BizError(42201, "类目不存在或不是物品类目")

    today_start = datetime.combine(datetime.now(LOCAL_TZ).date(), time.min, tzinfo=LOCAL_TZ)
    published_today = db.scalar(
        select(func.count())
        .select_from(Content)
        .where(Content.owner_id == user.id, Content.type == "item", Content.created_at >= today_start)
    )
    if published_today >= settings.DAILY_PUBLISH_LIMIT:
        raise BizError(42901, f"每天最多发布 {settings.DAILY_PUBLISH_LIMIT} 件物品，明天再来吧")

    # contents 和 items 两行在同一个事务里写入：commit 前任何一步出错都会整体回滚
    content = Content(
        type="item",
        owner_id=user.id,
        title=body.title,
        summary=body.summary or None,
        category_id=category.id,
        tags=body.tags,
        campus_area=body.campus_area or user.campus_area,
        status="pending",
        search_text=build_search_text(body.title, body.summary, body.tags),
        item=Item(
            price=body.price,
            original_price=body.original_price,
            condition=body.condition,
            images=body.images,
        ),
    )
    db.add(content)
    db.commit()

    return ok(to_detail(load_item(db, content.id), user), "发布成功，等待管理员审核")


@router.get("/{item_id}", response_model=ApiResponse[ItemDetailOut], summary="物品详情")
def get_item(
    item_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ItemDetailOut]:
    c = load_item(db, item_id)
    if c is None or c.status == "deleted":
        raise BizError(40401, "物品不存在")

    is_owner_or_admin = viewer is not None and (viewer.id == c.owner_id or viewer.role == "admin")
    # 待审核 / 被驳回 / 已下架的物品，只有卖家本人和管理员能看
    if c.status != "online" and not is_owner_or_admin:
        raise BizError(40401, "物品不存在")

    # 别人浏览已上架物品时浏览量 +1；用 SQL 自增，避免并发时丢计数
    if c.status == "online" and (viewer is None or viewer.id != c.owner_id):
        db.execute(update(Content).where(Content.id == c.id).values(view_count=Content.view_count + 1))
        db.commit()
        c.view_count += 1

    return ok(to_detail(c, viewer))
