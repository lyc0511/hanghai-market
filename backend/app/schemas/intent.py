from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class IntentCreateIn(BaseModel):
    item_id: int = Field(description="物品 id")
    message: str = Field(default="", max_length=200, description="给卖家的留言，可不填")

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        return v.strip()


class IntentItemBrief(BaseModel):
    id: int
    title: str
    price: float
    cover: str | None
    status: str


class UserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: str | None


class IntentOut(BaseModel):
    id: int
    status: str = Field(description="pending 待处理 / accepted 已接受 / rejected 已拒绝 / completed 已成交 / cancelled 已取消")
    my_role: str = Field(description="buyer：我是买家；seller：我是卖家")
    message: str | None
    item: IntentItemBrief
    counterpart: UserBrief = Field(description="交易对方")
    counterpart_wechat: str | None = Field(description="对方微信号，仅在已接受 / 已成交时返回")
    contact_revealed_at: datetime | None
    created_at: datetime
    updated_at: datetime
