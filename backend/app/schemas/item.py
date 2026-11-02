from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import CampusArea

ItemCondition = Literal["new", "like_new", "good", "fair"]


class ItemCreateIn(BaseModel):
    title: str = Field(description="标题，2–60 字")
    summary: str = Field(default="", max_length=300, description="描述，最多 300 字")
    category_id: int = Field(description="物品类目 id，来自 /api/meta/categories?type=item")
    price: Decimal = Field(ge=0, le=99999, decimal_places=2, description="售价，0 表示免费送")
    original_price: Decimal | None = Field(
        default=None, ge=0, le=99999, decimal_places=2, description="原价，可不填；填写时不能低于售价"
    )
    condition: ItemCondition = Field(description="成色：new / like_new / good / fair")
    images: list[str] = Field(description="图片路径，1–9 张，使用上传接口返回的 path")
    tags: list[str] = Field(default_factory=list, description="标签，最多 5 个，每个最多 10 字")
    campus_area: CampusArea | None = Field(default=None, description="交易校区，不填默认用个人资料里的校区")

    @field_validator("title")
    @classmethod
    def check_title(cls, v: str) -> str:
        v = v.strip()
        if not 2 <= len(v) <= 60:
            raise ValueError("标题应为 2–60 个字")
        return v

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, v: str) -> str:
        return v.strip()

    @field_validator("images")
    @classmethod
    def check_images(cls, v: list[str]) -> list[str]:
        if not 1 <= len(v) <= 9:
            raise ValueError("请上传 1–9 张图片")
        for p in v:
            # 只接受本站上传接口返回的路径，防止塞外链或 ../ 路径穿越
            if not p.startswith("/uploads/") or ".." in p:
                raise ValueError("图片路径不合法，请使用上传接口返回的 path")
        return v

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v: list[str]) -> list[str]:
        tags = list(dict.fromkeys(t.strip() for t in v if t.strip()))  # 去空白、去重、保持顺序
        if len(tags) > 5:
            raise ValueError("标签最多 5 个")
        if any(len(t) > 10 for t in tags):
            raise ValueError("每个标签最多 10 个字")
        return tags

    @model_validator(mode="after")
    def check_original_price(self) -> "ItemCreateIn":
        # 涉及两个字段的比较，要等所有字段都校验完再做
        if self.original_price is not None and self.original_price < self.price:
            raise ValueError("原价不能低于售价")
        return self


class CategoryBrief(BaseModel):
    id: int
    name: str


class SellerBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None
    campus_area: str | None


class ItemDetailOut(BaseModel):
    id: int
    title: str
    summary: str | None
    category: CategoryBrief | None
    tags: list[str]
    campus_area: str | None
    status: str
    reject_reason: str | None = Field(description="驳回原因，仅卖家本人和管理员可见")
    view_count: int
    price: float
    original_price: float | None
    condition: str
    images: list[str] = Field(description="图片完整访问地址")
    sold_at: datetime | None
    seller: SellerBrief
    is_mine: bool = Field(description="当前登录用户是否为卖家")
    created_at: datetime
    updated_at: datetime
