"""字典接口：枚举中文映射与类目列表，供前端下拉框、标签渲染使用。"""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import CAMPUS_AREAS
from app.db.session import get_db
from app.models import Category
from app.schemas.common import ApiResponse, ok
from app.schemas.meta import CategoryOut, EnumsOut

router = APIRouter(prefix="/meta", tags=["字典"])

ENUMS = EnumsOut(
    content_type={"item": "物品", "club": "社团", "activity": "活动"},
    content_status={
        "pending": "待审核",
        "online": "已上架",
        "offline": "已下架",
        "rejected": "已驳回",
        "deleted": "已删除",
    },
    item_condition={"new": "全新", "like_new": "几乎全新", "good": "轻微使用痕迹", "fair": "明显使用痕迹"},
    club_type={"academic": "学术科技", "art": "文艺兴趣", "sports": "体育运动", "public": "公益实践", "other": "其他"},
    intent_status={
        "pending": "待处理",
        "accepted": "已接受",
        "rejected": "已拒绝",
        "completed": "已成交",
        "cancelled": "已取消",
    },
    report_reason={
        "fraud": "疑似诈骗",
        "prohibited": "违禁物品",
        "false_info": "虚假信息",
        "spam": "广告刷屏",
        "abuse": "辱骂骚扰",
        "other": "其他",
    },
    campus_area=CAMPUS_AREAS,
)


@router.get("/enums", response_model=ApiResponse[EnumsOut], summary="枚举中文映射")
def get_enums() -> ApiResponse[EnumsOut]:
    return ok(ENUMS)


@router.get("/categories", response_model=ApiResponse[list[CategoryOut]], summary="类目列表")
def list_categories(
    type: Literal["item", "club"] | None = Query(default=None, description="item=物品类目，club=社团类目；不传返回全部"),
    db: Session = Depends(get_db),
) -> ApiResponse[list[CategoryOut]]:
    stmt = select(Category).order_by(Category.type, Category.sort_order, Category.id)
    if type is not None:
        stmt = stmt.where(Category.type == type)
    rows = db.scalars(stmt).all()
    return ok([CategoryOut.model_validate(r) for r in rows])
