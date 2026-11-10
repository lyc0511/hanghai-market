"""AI 助手的「登录用户专属」工具：查自己的信息 + 生成发布草稿。

安全原则：
    - 这些工具只在用户已登录时才发给大模型。
    - 查谁的数据由后端从登录令牌里取（ctx["user"]），工具参数里没有 user_id，模型无法指定别人。
    - 全部只读。prepare_item_draft 也只做校验、返回草稿，不写数据库；真正发布要用户在发布页上传照片并点提交，
      照常走管理员审核和每日发布上限。
    - 交易意向里对方的微信号不交给模型。
"""
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, get_args

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import activities as activity_api
from app.api import clubs as club_api
from app.api import intents as intent_api
from app.api import items as item_api
from app.api import notifications as notification_api
from app.core.config import settings
from app.core.constants import CAMPUS_AREAS
from app.models import Content, User
from app.schemas.assistant import AssistantCard, ItemDraft
from app.schemas.item import ItemCondition, ItemCreateIn

SIZE = 5
ITEM_STATUS = {"pending": "待审核", "online": "在售", "rejected": "被驳回", "offline": "已下架"}
INTENT_STATUS = {"pending": "待处理", "accepted": "已接受", "rejected": "已拒绝", "completed": "已成交", "cancelled": "已取消"}
APP_STATUS = {"pending": "待审核", "approved": "已通过", "rejected": "未通过"}
CONDITION_NAMES = {"new": "全新", "like_new": "几乎全新", "good": "轻微使用痕迹", "fair": "明显使用痕迹"}


def personal_tool_specs(item_categories: list[str]) -> list[dict[str, Any]]:
    def fn(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict:
        return {"type": "function", "function": {
            "name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []},
        }}

    return [
        fn("my_items", "查当前用户自己发布的物品及审核状态、驳回原因。",
           {"status": {"type": "string", "enum": list(ITEM_STATUS), "description": "不填返回全部"}}),
        fn("my_intents", "查当前用户的交易意向：我想买的（buyer）或别人想买我的（seller）。",
           {"role": {"type": "string", "enum": ["buyer", "seller"]},
            "status": {"type": "string", "enum": list(INTENT_STATUS)}}),
        fn("my_activities", "查当前用户报名的活动。",
           {"when": {"type": "string", "enum": ["upcoming", "ended"], "description": "默认 upcoming"}}),
        fn("my_clubs", "查当前用户加入的社团，以及入社申请的审核进度。", {}),
        fn("my_notifications", "查当前用户最近的站内通知。",
           {"unread_only": {"type": "boolean", "description": "true 只看未读"}}),
        fn("prepare_item_draft",
           "把用户想卖的东西整理成发布草稿（不会直接发布）。只有标题、类目、价格、成色都已从用户那里得到时才调用。",
           {
               "title": {"type": "string", "description": "标题，2–60 字，写清楚是什么"},
               "category": {"type": "string", "enum": item_categories},
               "price": {"type": "number", "minimum": 0, "description": "售价，0 表示免费送"},
               "condition": {"type": "string", "enum": list(get_args(ItemCondition)),
                             "description": "new 全新 / like_new 几乎全新 / good 轻微使用痕迹 / fair 明显使用痕迹"},
               "summary": {"type": "string", "description": "描述，最多 300 字，只写用户说过的信息"},
               "original_price": {"type": "number", "minimum": 0, "description": "原价，用户提到才填"},
               "tags": {"type": "array", "items": {"type": "string"}, "description": "最多 5 个，每个最多 10 字"},
               "campus_area": {"type": "string", "enum": CAMPUS_AREAS,
                               "description": "用户明确说了才填；不填自动用个人资料里的校区，不必追问"},
           },
           ["title", "category", "price", "condition"]),
    ]


def pick(v: Any, allowed) -> Any:
    return v if v in allowed else None


# ---------------------------------------------------------------- 查自己的信息（直接调用现有的「我的」接口函数）

def run_my_items(db: Session, args: dict, ctx: dict) -> tuple[dict, list[AssistantCard]]:
    page = item_api.list_my_items(status=pick(args.get("status"), ITEM_STATUS), page=1, page_size=SIZE,
                                  user=ctx["user"], db=db).data
    results, cards = [], []
    for it in page.items:
        link = f"/items/{it.id}"
        results.append({"id": it.id, "title": it.title, "price": it.price, "status": ITEM_STATUS.get(it.status, it.status),
                        "sold": it.sold, "reject_reason": it.reject_reason, "link": link})
        cards.append(AssistantCard(type="item", id=it.id, title=it.title, link=link, cover=it.cover,
                                   subtitle=("已售出" if it.sold else ITEM_STATUS.get(it.status, it.status))))
    return {"total": page.total, "results": results, "manage_link": "/me/items"}, cards


def run_my_intents(db: Session, args: dict, ctx: dict) -> tuple[dict, list[AssistantCard]]:
    page = intent_api.list_my_intents(role=pick(args.get("role"), ("buyer", "seller")),
                                      status=pick(args.get("status"), INTENT_STATUS),
                                      page=1, page_size=SIZE, user=ctx["user"], db=db).data
    results = [{
        # 注意：不放 counterpart_wechat（对方微信号），模型拿不到
        "item": t.item.title, "price": t.item.price, "my_role": "买家" if t.my_role == "buyer" else "卖家",
        "counterpart": t.counterpart.nickname, "status": INTENT_STATUS.get(t.status, t.status),
        "link": f"/me/intents?role={t.my_role}",
    } for t in page.items]
    return {"total": page.total, "results": results}, []


def run_my_activities(db: Session, args: dict, ctx: dict) -> tuple[dict, list[AssistantCard]]:
    page = activity_api.my_activities(when=pick(args.get("when"), ("upcoming", "ended")) or "upcoming",
                                      page=1, page_size=SIZE, user=ctx["user"], db=db).data
    results, cards = [], []
    for a in page.items:
        link = f"/activities/{a.id}"
        start = a.start_time.astimezone(ctx["tz"]).strftime("%m月%d日 %H:%M")
        results.append({"title": a.title, "club": a.club.title, "start": start, "location": a.location, "link": link})
        cards.append(AssistantCard(type="activity", id=a.id, title=a.title, link=link, subtitle=f"{start} · {a.location}"))
    return {"total": page.total, "results": results}, cards


def run_my_clubs(db: Session, args: dict, ctx: dict) -> tuple[dict, list[AssistantCard]]:
    user = ctx["user"]
    clubs = club_api.my_clubs(page=1, page_size=SIZE, user=user, db=db).data
    apps = club_api.my_applications(status=None, page=1, page_size=SIZE, user=user, db=db).data
    cards = [AssistantCard(type="club", id=c.id, title=c.title, link=f"/clubs/{c.id}", cover=c.logo_url,
                           subtitle="会长" if c.my_role == "president" else "成员") for c in clubs.items]
    return {
        "joined": [{"name": c.title, "my_role": "会长" if c.my_role == "president" else "成员",
                    "pending_applications_to_review": c.pending_count, "link": f"/clubs/{c.id}"} for c in clubs.items],
        "applications": [{"club": a.club_title, "status": APP_STATUS.get(a.status, a.status), "link": f"/clubs/{a.club_id}"}
                         for a in apps.items],
        "manage_link": "/me/clubs",
    }, cards


def run_my_notifications(db: Session, args: dict, ctx: dict) -> tuple[dict, list[AssistantCard]]:
    page = notification_api.list_notifications(unread_only=args.get("unread_only") is True, page=1, page_size=SIZE,
                                               user=ctx["user"], db=db).data
    results = [{"title": n.title, "body": n.body, "read": n.is_read, "link": n.link} for n in page.items]
    return {"total": page.total, "results": results, "all_link": "/notifications"}, []


# ---------------------------------------------------------------- 生成发布草稿

def to_decimal(v: Any) -> Decimal | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def published_today(db: Session, user: User, tz) -> int:
    start = datetime.combine(datetime.now(tz).date(), time.min, tzinfo=tz)
    return db.scalar(select(func.count()).select_from(Content).where(
        Content.owner_id == user.id, Content.type == "item", Content.created_at >= start)) or 0


def run_prepare_item_draft(db: Session, args: dict, ctx: dict) -> tuple[dict, list[AssistantCard]]:
    """用发布接口的同一个校验模型 ItemCreateIn 检查草稿：规则只有一份，不会和发布页不一致。

    图片要用户在发布页自己上传，这里先放一个占位路径只为通过「1–9 张图片」的校验，不会返回给前端。
    """
    user: User = ctx["user"]
    category_id = ctx["item_category_ids"].get(args.get("category"))
    if category_id is None:
        return {"ok": False, "errors": ["类目无效，请从物品类目里选一个"]}, []
    remaining = settings.DAILY_PUBLISH_LIMIT - published_today(db, user, ctx["tz"])
    if remaining <= 0:
        return {"ok": False, "errors": [f"你今天已经发布了 {settings.DAILY_PUBLISH_LIMIT} 件，明天再来吧"]}, []

    tags = args.get("tags") if isinstance(args.get("tags"), list) else []
    try:
        data = ItemCreateIn(
            title=str(args.get("title") or ""),
            summary=str(args.get("summary") or "")[:300],
            category_id=category_id,
            price=to_decimal(args.get("price")),
            original_price=to_decimal(args.get("original_price")),
            condition=args.get("condition"),
            images=["/uploads/assistant-draft-placeholder.jpg"],
            tags=[str(t) for t in tags][:5],
            campus_area=pick(args.get("campus_area"), CAMPUS_AREAS) or user.campus_area,
        )
    except ValidationError as e:
        # 把校验错误交回模型，让它向用户确认后重新生成
        return {"ok": False, "errors": [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]}, []

    ctx["draft"] = ItemDraft(
        title=data.title, summary=data.summary, category_id=category_id, category_name=args.get("category"),
        price=float(data.price), original_price=float(data.original_price) if data.original_price is not None else None,
        condition=data.condition, condition_name=CONDITION_NAMES[data.condition], tags=data.tags,
        campus_area=data.campus_area,
    )
    return {"ok": True, "draft": ctx["draft"].model_dump(), "today_remaining": remaining,
            "next_step": "草稿卡片已显示给用户，请用户点「去发布页确认」，上传 1–9 张照片后提交，提交后需管理员审核"}, []


PERSONAL_TOOLS = {
    "my_items": run_my_items,
    "my_intents": run_my_intents,
    "my_activities": run_my_activities,
    "my_clubs": run_my_clubs,
    "my_notifications": run_my_notifications,
    "prepare_item_draft": run_prepare_item_draft,
}
