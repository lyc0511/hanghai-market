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


# ------------------------------------------------------------ 登录用户专属：查自己的信息

def tools_sent(seen):
    return {t["function"]["name"] for t in seen[0]["tools"]}


def tool_message(seen, i=1):
    """第 i 次请求时模型收到的最后一条工具结果（解析成 dict）。"""
    return json.loads(seen[i]["messages"][-1]["content"])


def test_personal_tools_only_for_logged_in(client, monkeypatch, make_user):
    seen = fake_llm(monkeypatch, [{"content": "请先登录"}])
    ask(client, "我发布的东西审核了吗")
    assert not any(n.startswith("my_") for n in tools_sent(seen)) and "prepare_item_draft" not in tools_sent(seen)

    # 游客即使让模型「硬调」个人工具，后端也不执行
    seen = fake_llm(monkeypatch, [tool_call("my_items", {}), {"content": "好"}])
    ask(client, "我发布的")
    assert "error" in tool_message(seen)

    _, h = make_user("登录用户")
    seen = fake_llm(monkeypatch, [{"content": "好"}])
    ask(client, "你好", h)
    assert {"my_items", "my_intents", "my_activities", "my_clubs", "my_notifications", "prepare_item_draft"} <= tools_sent(seen)


def test_my_items_only_returns_own(client, db, make_user, item_category_id, monkeypatch):
    me, hm = make_user("我")
    _, ho = make_user("别人")
    mine = publish_item(client, hm, item_category_id, title="我的台灯")["data"]["id"]
    other = publish_item(client, ho, item_category_id, title="别人的台灯")["data"]["id"]
    db.get(Content, mine).status = "rejected"
    db.get(Content, mine).reject_reason = "图片不清晰"
    db.flush()

    # 模型就算在参数里塞 user_id，也会被忽略：用户只从登录令牌来
    seen = fake_llm(monkeypatch, [tool_call("my_items", {"user_id": 1, "owner_id": 1}), {"content": "好"}])
    r = ask(client, "我的东西为什么没上架", hm)
    result = tool_message(seen)
    ids = [x["id"] for x in result["results"]]
    assert mine in ids and other not in ids
    assert result["results"][0]["status"] == "被驳回" and result["results"][0]["reject_reason"] == "图片不清晰"
    assert [c["id"] for c in r["data"]["cards"]] == [mine]


def test_my_intents_hide_wechat(client, db, make_user, item_category_id, monkeypatch):
    seller, hs, item_id = online_item(client, db, make_user, item_category_id)
    _, hb = make_user("买家", wechat="secret_wx_123")
    iid = call(client, "POST", "/intents", hb, json={"item_id": item_id})["data"]["id"]
    assert call(client, "POST", f"/intents/{iid}/accept", hs)["code"] == 0  # 已接受：网页上卖家能看到买家微信

    seen = fake_llm(monkeypatch, [tool_call("my_intents", {"role": "seller"}), {"content": "好"}])
    ask(client, "谁想买我的东西", hs)
    raw = seen[1]["messages"][-1]["content"]
    assert "secret_wx_123" not in raw  # 但不交给大模型
    assert json.loads(raw)["results"][0]["status"] == "已接受"


def test_other_personal_tools_run(client, make_user, monkeypatch):
    _, h = make_user("新同学")
    seen = fake_llm(monkeypatch, [
        {"content": "", "tool_calls": [
            {"id": "a", "function": {"name": "my_activities", "arguments": "{}"}},
            {"id": "b", "function": {"name": "my_clubs", "arguments": "{}"}},
            {"id": "c", "function": {"name": "my_notifications", "arguments": json.dumps({"unread_only": True})}},
        ]},
        {"content": "你还没有报名活动"},
    ])
    r = ask(client, "看看我的情况", h)
    assert r["code"] == 0
    results = [json.loads(m["content"]) for m in seen[1]["messages"] if m["role"] == "tool"]
    assert results[0]["total"] == 0 and results[1]["joined"] == [] and results[2]["total"] == 0


# ------------------------------------------------------------ 对话生成发布草稿

DRAFT = {"title": "护眼台灯", "price": 30, "condition": "good", "summary": "用了一学期，三档调光", "tags": ["台灯", "宿舍"]}


def category_name(db, cid):
    from app.models import Category
    return db.get(Category, cid).name


def test_draft_is_validated_and_not_saved(client, db, make_user, item_category_id, monkeypatch):
    from sqlalchemy import func
    _, h = make_user("卖家")
    before = db.scalar(select(func.count()).select_from(Content))
    fake_llm(monkeypatch, [
        tool_call("prepare_item_draft", {**DRAFT, "category": category_name(db, item_category_id)}),
        {"content": "草稿好了，点下方去发布页确认"},
    ])
    r = ask(client, "帮我卖台灯，30 块，轻微使用痕迹", h)
    d = r["data"]["draft"]
    assert d["title"] == "护眼台灯" and d["category_id"] == item_category_id and d["price"] == 30
    assert d["condition_name"] == "轻微使用痕迹" and d["campus_area"] == "黄埔校区"  # 没说校区就用个人资料里的
    assert db.scalar(select(func.count()).select_from(Content)) == before  # 只生成草稿，不写数据库
    assert last_log(db).intent == "draft"


def test_draft_errors_go_back_to_model(client, db, make_user, item_category_id, monkeypatch):
    _, h = make_user("卖家")
    cat = category_name(db, item_category_id)
    seen = fake_llm(monkeypatch, [
        tool_call("prepare_item_draft", {**DRAFT, "category": cat, "title": "灯"}),
        tool_call("prepare_item_draft", {**DRAFT, "category": cat, "original_price": 10}, "call_2"),
        tool_call("prepare_item_draft", {**DRAFT, "category": "不存在的类目"}, "call_3"),
        {"content": "标题太短了，能再具体点吗？"},
    ])
    r = ask(client, "卖灯", h)
    results = [tool_message(seen, i) for i in (1, 2, 3)]
    assert all(x["ok"] is False for x in results)
    assert "标题" in results[0]["errors"][0]  # 与发布接口同一套规则
    assert "原价" in results[1]["errors"][0]
    assert "类目" in results[2]["errors"][0]
    assert r["data"]["draft"] is None


def test_draft_respects_daily_limit(client, db, make_user, item_category_id, monkeypatch):
    _, h = make_user("卖家")
    monkeypatch.setattr(assistant.settings, "DAILY_PUBLISH_LIMIT", 1)
    publish_item(client, h, item_category_id)
    seen = fake_llm(monkeypatch, [
        tool_call("prepare_item_draft", {**DRAFT, "category": category_name(db, item_category_id)}),
        {"content": "今天发不了了"},
    ])
    r = ask(client, "再卖一个", h)
    assert tool_message(seen)["ok"] is False and r["data"]["draft"] is None


# ------------------------------------------------------------ 全站每日上限

def test_global_daily_quota_falls_back(client, db, monkeypatch):
    """全站今天调用大模型的次数到上限后，不再请求大模型，自动降级；降级的回答不计入额度。"""
    from datetime import datetime
    from sqlalchemy import func
    today_start = datetime.combine(datetime.now(assistant.LOCAL_TZ).date(), datetime.min.time(), tzinfo=assistant.LOCAL_TZ)
    used_before = db.scalar(select(func.count()).select_from(AiMessage).where(
        AiMessage.created_at >= today_start, AiMessage.fallback.is_(False)))
    monkeypatch.setattr(assistant.settings, "ASSISTANT_GLOBAL_PER_DAY", used_before + 1)

    seen = fake_llm(monkeypatch, [{"content": "第一次正常回答"}])
    r1 = ask(client, "第一个问题")
    assert r1["data"]["fallback"] is False and len(seen) == 1

    r2 = ask(client, "第二个问题")  # 额度已满：不再调用大模型
    assert r2["data"]["fallback"] is True and len(seen) == 1
    r3 = ask(client, "第三个问题")  # 降级的那次不计数，所以仍是满的
    assert r3["data"]["fallback"] is True and len(seen) == 1

    monkeypatch.setattr(assistant.settings, "ASSISTANT_GLOBAL_PER_DAY", 0)  # 0 = 不限制
    fake_llm(monkeypatch, [{"content": "不限制时正常"}])
    assert ask(client, "第四个问题")["data"]["fallback"] is False
