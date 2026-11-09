"""大模型接口的最小封装（DeepSeek，OpenAI 兼容格式）。

只做一件事：把 messages + tools 发给 /chat/completions，返回模型的那条回复消息。
不引入 openai SDK，直接用 httpx 发 HTTP 请求，方便看清楚到底发了什么。

文档：https://api-docs.deepseek.com/
"""
from typing import Any

import httpx

from app.core.config import settings


class LlmError(Exception):
    """大模型不可用：没配置 Key、网络超时、接口报错、余额不足等。调用方统一按「降级」处理。"""


def llm_enabled() -> bool:
    return bool(settings.LLM_API_KEY)


def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """发一次对话请求，返回 choices[0].message（含 content 和可能的 tool_calls）。"""
    if not llm_enabled():
        raise LlmError("未配置 LLM_API_KEY")

    body: dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.3,  # 找东西要稳定，不需要发挥创意
        "max_tokens": 800,
        "stream": False,
        # 关闭「思考模式」：导航类问题不需要长推理，响应更快、更省钱
        "thinking": {"type": "disabled"},
    }
    if tools:
        body["tools"] = tools

    url = settings.LLM_API_BASE.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    try:
        r = httpx.post(url, json=body, headers=headers, timeout=settings.LLM_TIMEOUT_SECONDS)
    except httpx.HTTPError as e:
        raise LlmError(f"请求大模型失败：{type(e).__name__}") from e
    if r.status_code != 200:
        # 401 Key 错误、402 余额不足、429 限流、5xx 服务端故障……原文只写日志，不返回给用户
        raise LlmError(f"大模型接口返回 {r.status_code}：{r.text[:200]}")
    try:
        return r.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError) as e:
        raise LlmError("大模型返回格式异常") from e
