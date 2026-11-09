from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatIn(BaseModel):
    """前端把本次对话的历史一起发过来（服务端不保存上下文），最后一条必须是用户的新问题。"""

    session_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$", description="前端生成的会话 id，用于记录日志")
    messages: list[ChatTurn] = Field(min_length=1, max_length=40)

    @field_validator("messages")
    @classmethod
    def last_is_question(cls, v: list[ChatTurn]) -> list[ChatTurn]:
        last = v[-1]
        if last.role != "user":
            raise ValueError("最后一条消息必须是用户的提问")
        if len(last.content.strip()) == 0 or len(last.content) > 300:
            raise ValueError("提问需在 1–300 字之间")
        return v


class AssistantCard(BaseModel):
    """助手找到的结果，前端渲染成可点击的卡片。"""

    type: Literal["item", "club", "activity"]
    id: int
    title: str
    subtitle: str
    link: str
    cover: str | None = None


class ChatOut(BaseModel):
    reply: str
    cards: list[AssistantCard]
    # true 表示大模型不可用，本次是关键词搜索兜底的结果
    fallback: bool
