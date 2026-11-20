"""主要业务流程测试：登录鉴权、发布审核、交易意向、举报、通知、封禁。"""
from sqlalchemy import select

from app.models import Content, Notification
from tests.conftest import call


def publish_item(client, headers, category_id, title="测试物品 台灯"):
    body = {
        "title": title,
        "summary": "九成新，宿舍自提",
        "category_id": category_id,
        "price": "25",
        "condition": "like_new",
        "images": ["/uploads/test/demo.jpg"],
        "tags": ["台灯"],
    }
    return call(client, "POST", "/items", headers, json=body)


# ------------------------------------------------------------ 鉴权

def test_auth_required_and_login_errors(client):
    assert call(client, "GET", "/auth/me")["code"] == 40100
    r = call(client, "POST", "/auth/login", json={"student_no": "20230002", "password": "Wrong1234"})
    assert r["code"] == 40101


def test_me_and_admin_guard(client, make_user):
    _, h = make_user("小明")
    me = call(client, "GET", "/auth/me", h)
    assert me["code"] == 0 and me["data"]["nickname"] == "小明"
    assert call(client, "GET", "/admin/dashboard", h)["code"] == 40300


def test_password_change_revokes_both_sessions(client, make_user):
    _, unrelated = make_user()
    credentials = {"student_no": "29963333", "password": "FirstPass123"}
    first = call(client, "POST", "/auth/register", json={**credentials, "nickname": "改密测试"})
    second = call(client, "POST", "/auth/login", json=credentials)
    sessions = [{"Authorization": "Bearer " + r["data"]["access_token"]} for r in (first, second)]
    assert sessions[0] != sessions[1]
    change = {"old_password": credentials["password"], "new_password": "SecondPass123"}
    assert call(client, "POST", "/auth/password", sessions[0], json={**change, "old_password": "Wrong1234"})["code"] == 40103
    assert call(client, "GET", "/auth/me", sessions[1])["code"] == 0
    assert call(client, "POST", "/auth/password", sessions[0], json=change)["code"] == 0
    for headers in sessions:
        assert call(client, "GET", "/auth/me", headers)["code"] == 40100
    assert call(client, "GET", "/auth/me", unrelated)["code"] == 0
    assert call(client, "POST", "/auth/login", json=credentials)["code"] == 40101
    fresh = call(client, "POST", "/auth/login", json={**credentials, "password": change["new_password"]})
    assert call(client, "GET", "/auth/me", {"Authorization": "Bearer " + fresh["data"]["access_token"]})["code"] == 0


# ------------------------------------------------------------ 发布 → 审核

def test_publish_then_admin_approve(client, db, make_user, item_category_id):
    seller, hs = make_user("卖家")
    _, ha = make_user("管理员", role="admin")

    r = publish_item(client, hs, item_category_id)
    assert r["code"] == 0 and r["data"]["status"] == "pending"
    item_id = r["data"]["id"]

    # 待审核的物品不出现在公开列表里
    listed = call(client, "GET", "/items", params={"keyword": "测试物品 台灯"})["data"]["items"]
    assert item_id not in [i["id"] for i in listed]

    r = call(client, "POST", f"/admin/items/{item_id}/approve", ha)
    assert r["code"] == 0 and r["data"]["status"] == "online"
    # 再审一次：状态不对
    assert call(client, "POST", f"/admin/items/{item_id}/approve", ha)["code"] == 40902
    # 卖家收到通知
    n = db.scalar(select(Notification).where(Notification.user_id == seller.id, Notification.type == "content_approved"))
    assert n is not None and n.link == f"/items/{item_id}"


def online_item(client, db, make_user, category_id):
    seller, hs = make_user("卖家")
    item_id = publish_item(client, hs, category_id)["data"]["id"]
    db.get(Content, item_id).status = "online"
    db.flush()
    return seller, hs, item_id


# ------------------------------------------------------------ 交易意向

def test_intent_full_flow(client, db, make_user, item_category_id):
    seller, hs, item_id = online_item(client, db, make_user, item_category_id)
    _, hb1 = make_user("买家甲", wechat="buyer_a")
    _, hb2 = make_user("买家乙", wechat="buyer_b")

    assert call(client, "POST", "/intents", hs, json={"item_id": item_id})["code"] == 42203  # 不能买自己的
    i1 = call(client, "POST", "/intents", hb1, json={"item_id": item_id, "message": "还在吗"})
    assert i1["code"] == 0 and i1["data"]["counterpart_wechat"] is None  # 接受前看不到微信
    assert call(client, "POST", "/intents", hb1, json={"item_id": item_id})["code"] == 40903  # 不能重复
    i2 = call(client, "POST", "/intents", hb2, json={"item_id": item_id})
    id1, id2 = i1["data"]["id"], i2["data"]["id"]

    assert call(client, "POST", f"/intents/{id1}/accept", hb1)["code"] == 40301  # 买家不能接受
    acc = call(client, "POST", f"/intents/{id1}/accept", hs)
    assert acc["data"]["status"] == "accepted" and acc["data"]["counterpart_wechat"] == "buyer_a"

    done = call(client, "POST", f"/intents/{id1}/complete", hs)
    assert done["code"] == 0 and done["data"]["status"] == "completed"
    assert db.get(Content, item_id).status == "offline"  # 成交自动下架
    other = call(client, "GET", "/intents/mine", hb2)["data"]["items"][0]
    assert other["id"] == id2 and other["status"] == "rejected"  # 其余意向自动关闭


def test_intent_requires_wechat(client, db, make_user, item_category_id):
    _, _, item_id = online_item(client, db, make_user, item_category_id)
    _, hb = make_user("没填微信", wechat=None)
    assert call(client, "POST", "/intents", hb, json={"item_id": item_id})["code"] == 42202


# ------------------------------------------------------------ 举报

def test_report_rules_and_takedown(client, db, make_user, item_category_id):
    seller, hs, item_id = online_item(client, db, make_user, item_category_id)
    reporter1, h1 = make_user("举报人甲")
    reporter2, h2 = make_user("举报人乙")
    _, ha = make_user("管理员", role="admin")
    target = {"target_type": "item", "target_id": item_id}

    assert call(client, "POST", "/reports", hs, json={**target, "reason": "spam"})["code"] == 42251  # 不能举报自己
    assert call(client, "POST", "/reports", h1, json={**target, "reason": "other"})["code"] == 42252  # 其他须说明
    assert call(client, "POST", "/reports", h1, json={"target_type": "club", "target_id": item_id, "reason": "spam"})["code"] == 40451
    r1 = call(client, "POST", "/reports", h1, json={**target, "reason": "fraud", "description": "要求先转账"})
    assert r1["code"] == 0
    assert call(client, "POST", "/reports", h1, json={**target, "reason": "spam"})["code"] == 40951  # 重复
    r2 = call(client, "POST", "/reports", h2, json={**target, "reason": "false_info"})

    assert call(client, "GET", "/admin/reports", h1)["code"] == 40300
    handled = call(client, "POST", f"/admin/reports/{r1['data']['id']}/handle", ha,
                   json={"action": "resolve", "note": "经核实违规", "takedown": True})
    assert handled["code"] == 0 and handled["data"]["status"] == "resolved"
    assert db.get(Content, item_id).status == "offline"

    # 同一内容的另一条举报被一并办结
    mine2 = call(client, "GET", "/reports/mine", h2)["data"]["items"][0]
    assert mine2["id"] == r2["data"]["id"] and mine2["status"] == "resolved"
    # 举报人、发布者都收到通知
    types = set(db.scalars(select(Notification.type).where(Notification.user_id.in_([reporter1.id, reporter2.id, seller.id]))))
    assert {"report_resolved", "content_takedown"} <= types
    # 已处理的不能再处理
    again = call(client, "POST", f"/admin/reports/{r1['data']['id']}/handle", ha, json={"action": "dismiss", "note": "x"})
    assert again["code"] == 40952


# ------------------------------------------------------------ 通知

def test_notifications_read_and_ownership(client, db, make_user):
    u1, h1 = make_user("甲")
    _, h2 = make_user("乙")
    for i in range(3):
        db.add(Notification(user_id=u1.id, type="test", title=f"通知{i}", body="内容", link="/"))
    db.flush()

    assert call(client, "GET", "/notifications/unread-count", h1)["data"]["count"] == 3
    first = call(client, "GET", "/notifications", h1)["data"]["items"][0]
    assert call(client, "POST", f"/notifications/{first['id']}/read", h2)["code"] == 40461  # 别人的
    assert call(client, "POST", f"/notifications/{first['id']}/read", h1)["data"]["count"] == 2
    assert call(client, "POST", "/notifications/read-all", h1)["data"]["count"] == 0
    assert call(client, "GET", "/notifications", h1, params={"unread_only": True})["data"]["total"] == 0


# ------------------------------------------------------------ 封禁

def test_ban_blocks_user_and_offlines_items(client, db, make_user, item_category_id):
    seller, hs, item_id = online_item(client, db, make_user, item_category_id)
    admin, ha = make_user("管理员", role="admin")
    _, ha2 = make_user("另一个管理员", role="admin")

    assert call(client, "POST", f"/admin/users/{admin.id}/ban", ha, json={"reason": "测试"})["code"] == 40371  # 自己
    assert call(client, "POST", f"/admin/users/{admin.id}/ban", ha2, json={"reason": "测试"})["code"] == 40371  # 管理员

    r = call(client, "POST", f"/admin/users/{seller.id}/ban", ha, json={"reason": "发布虚假信息", "offline_items": True})
    assert r["code"] == 0 and r["data"]["status"] == "banned"
    assert db.get(Content, item_id).status == "offline"
    assert call(client, "GET", "/auth/me", hs)["code"] == 40300  # 旧令牌立即失效

    assert call(client, "POST", f"/admin/users/{seller.id}/unban", ha)["data"]["status"] == "active"
    assert call(client, "GET", "/auth/me", hs)["code"] == 0
    actions = [a["action"] for a in call(client, "GET", "/admin/audit-logs", ha)["data"]["items"][:2]]
    assert actions == ["unban_user", "ban_user"]
