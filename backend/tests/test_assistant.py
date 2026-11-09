"""AI 助手测试：不真正调用 DeepSeek，用假的 llm.chat 模拟大模型的回复，既不花钱也结果稳定。"""
import json

import pytest
from sqlalchemy import select

from app.api import assistant
from app.core import llm
from app.models import AiMessage, Content
from tests.conftest import call
from tests.test_flows import online_item, publish_item

SESSION = "test-session-0001"


@pytest.fixture(autouse=True)
def reset_limiter():
    assistant.limiter.reset()
    yield
    assistant.limiter.reset()


def ask(client, question, headers=None, history=()):
    body = {"session_id": SESSION, "messages": [*history, {"role": "user", "content": question}]}
    return call(client, "POST", "/assistant/chat", headers, json=body)


def fake_llm(monkeypatch, replies):
    """按顺序返回预设的模型消息，并记下每次收到的 messages。"""
    seen = []
    queue = list(replies)

    def _chat(messages, tools=None):
        seen.append({"messages": [dict(m) for m in messages], "tools": tools})
        return queue.pop(0)

    monkeypatch.setattr(assistant.llm, "chat", _chat)
    return seen


def tool_call(name, args, call_id="call_1"):
    arguments = args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
    return {"content": "", "tool_calls": [{"id": call_id, "type": "function",
                                           "function": {"name": name, "arguments": arguments}}]}


def last_log(db):
    return db.scalar(select(AiMessage).where(AiMessage.session_id == SESSION).order_by(AiMessage.id.desc()))


# ------------------------------------------------------------ 工具调用

def test_tool_call_returns_real_online_items(client, db, make_user, item_category_id, monkeypatch):
    _, _, item_id = online_item(client, db, make_user, item_category_id)  # 标题「测试物品 台灯」
    _, hs = make_user("另一个卖家")
    pending_id = publish_item(client, hs, item_category_id, title="测试物品 台灯 待审")["data"]["id"]

    seen = fake_llm(monkeypatch, [
        tool_call("search_items", {"keyword": "测试物品", "price_max": 30}),
        {"content": f"找到一盏台灯，[点这里看看](/items/{item_id})"},
    ])
    r = ask(client, "有没有 30 块以内的台灯")

    assert r["code"] == 0 and r["data"]["fallback"] is False
    ids = [c["id"] for c in r["data"]["cards"]]
    assert item_id in ids and pending_id not in ids  # 待审核的不会被助手找出来
    card = next(c for c in r["data"]["cards"] if c["id"] == item_id)
    assert card["link"] == f"/items/{item_id}" and card["subtitle"].startswith("¥25")
    assert assistant.fmt_price(0) == "免费送" and assistant.fmt_price(12.5) == "¥12.5"

    # 第二次请求时，模型能看到工具结果（按协议：assistant 的 tool_calls + role=tool 的结果）
    second = seen[1]["messages"]
    assert second[-2]["tool_calls"][0]["id"] == "call_1"
    assert second[-1]["role"] == "tool" and second[-1]["tool_call_id"] == "call_1"
    assert "wechat" not in second[-1]["content"]

    log = last_log(db)
    assert log.intent == "items" and log.fallback is False and item_id in log.result_ids
    assert log.slots["calls"][0]["args"]["price_max"] == 30


def test_guide_question_without_tools(client, db, monkeypatch):
    seen = fake_llm(monkeypatch, [{"content": "点右上角「发布闲置」，或进入 [发布页](/publish)。"}])
    r = ask(client, "怎么卖东西？", history=[{"role": "user", "content": "你好"},
                                          {"role": "assistant", "content": "你好，我是小航"}])
    assert r["code"] == 0 and r["data"]["cards"] == [] and "/publish" in r["data"]["reply"]
    sent = seen[0]["messages"]
    assert sent[0]["role"] == "system" and "使用说明" in sent[0]["content"]
    assert sent[1]["role"] == "system" and "未登录" in sent[1]["content"]
    assert [m["role"] for m in sent[2:]] == ["user", "assistant", "user"]
    assert {t["function"]["name"] for t in seen[0]["tools"]} == {"search_items", "search_clubs", "search_activities"}
    assert last_log(db).intent == "guide"


def test_static_prompt_is_shared_for_cache(make_user):
    """省钱的关键：第一条系统消息对所有用户、每一天都完全相同，DeepSeek 才能命中缓存。"""
    u1, _ = make_user("甲同学")
    u2, _ = make_user("乙同学")
    cats = ["教材", "数码"]
    guest, a, b = (assistant.system_messages(u, cats) for u in (None, u1, u2))
    assert guest[0] == a[0] == b[0]
    assert "甲同学" not in a[0]["content"] and "甲同学" in a[1]["content"]
    assert "今天是" not in a[0]["content"]


def test_bad_tool_arguments_do_not_crash(client, monkeypatch):
    fake_llm(monkeypatch, [
        {"content": "", "tool_calls": [
            {"id": "a", "function": {"name": "search_items", "arguments": "{不是 JSON"}},
            {"id": "b", "function": {"name": "search_items",
                                     "arguments": json.dumps({"condition": "破烂", "price_min": -5, "campus_area": "火星"})}},
            {"id": "c", "function": {"name": "delete_everything", "arguments": "{}"}},
            {"id": "d", "function": {"name": "search_activities", "arguments": json.dumps({"when": "yesterday"})}},
            {"id": "e", "function": {"name": "search_clubs", "arguments": json.dumps({"recruiting": "yes"})}},
        ]},
        {"content": "好的"},
    ])
    r = ask(client, "随便找找")
    assert r["code"] == 0 and r["data"]["reply"] == "好的"


def test_tool_rounds_are_capped(client, monkeypatch):
    replies = [tool_call("search_clubs", {"keyword": "篮球"}, f"c{i}") for i in range(assistant.MAX_ROUNDS)]
    seen = fake_llm(monkeypatch, [*replies, {"content": "总结"}])
    r = ask(client, "篮球社")
    assert r["data"]["reply"] == "总结"
    assert len(seen) == assistant.MAX_ROUNDS + 1 and seen[-1]["tools"] is None  # 最后一次不再给工具


# ------------------------------------------------------------ 降级

def test_fallback_when_llm_unavailable(client, db, make_user, item_category_id, monkeypatch):
    _, _, item_id = online_item(client, db, make_user, item_category_id)

    def broken(messages, tools=None):
        raise llm.LlmError("超时")

    monkeypatch.setattr(assistant.llm, "chat", broken)
    r = ask(client, "有没有测试物品呀？")
    assert r["code"] == 0 and r["data"]["fallback"] is True
    assert item_id in [c["id"] for c in r["data"]["cards"]]
    assert last_log(db).intent == "fallback"

    r = ask(client, "我想了解一下这个网站平时都是怎么运作的")
    assert r["data"]["fallback"] is True and r["data"]["cards"] == [] and "/market" in r["data"]["reply"]


def test_no_api_key_means_fallback(client, monkeypatch):
    monkeypatch.setattr(llm.settings, "LLM_API_KEY", "")
    r = ask(client, "社团")
    assert r["code"] == 0 and r["data"]["fallback"] is True


# ------------------------------------------------------------ 校验与限流

def test_validation_and_rate_limit(client, make_user, monkeypatch):
    fake_llm(monkeypatch, [{"content": "ok"}] * 10)
    bad = {"session_id": SESSION, "messages": [{"role": "assistant", "content": "我先说"}]}
    assert call(client, "POST", "/assistant/chat", json=bad)["code"] == 40000
    assert ask(client, "x" * 301)["code"] == 40000

    monkeypatch.setattr(assistant.settings, "ASSISTANT_PER_MINUTE", 2)
    _, h = make_user("提问者")
    assert ask(client, "1", h)["code"] == 0
    assert ask(client, "2", h)["code"] == 0
    assert ask(client, "3", h)["code"] == 42981
    assert ask(client, "游客不受该用户限制")["code"] == 0  # 游客按 IP 单独计数
