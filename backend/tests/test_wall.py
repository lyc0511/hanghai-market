"""校园墙测试：先审后发的流程、匿名不泄露、越权防护、投稿限制。"""
import json

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import AuditLog, Category, Content, Notification, Post
from tests.conftest import call

# 投稿人昵称故意起得很特别：只要它出现在别人能拿到的响应里，就说明匿名漏了
AUTHOR_NICK = "投稿人甲乙丙丁"


@pytest.fixture()
def tags(db) -> dict[str, int]:
    """帖子标签：slug -> id"""
    return {c.slug: c.id for c in db.scalars(select(Category).where(Category.type == "post"))}


def submit(client, headers, tag_id, body="在图书馆三楼捡到一张校园卡，失主联系我"):
    return call(client, "POST", "/posts", headers, json={"body": body, "tag_id": tag_id})


def approve(client, admin_headers, post_id):
    return call(client, "POST", f"/admin/posts/{post_id}/approve", admin_headers)


def feed_ids(client, headers, **params):
    return [p["id"] for p in call(client, "GET", "/posts", headers, params=params)["data"]["items"]]


# ------------------------------------------------------------ 登录与参数校验

def test_wall_requires_login(client, make_user, tags):
    # 游客：不能看墙、不能看详情、不能投稿
    assert call(client, "GET", "/posts")["code"] == 40100
    assert call(client, "GET", "/posts/1")["code"] == 40100
    assert submit(client, None, tags["help"])["code"] == 40100


def test_submit_validation(client, make_user, tags, item_category_id):
    _, h = make_user()
    assert submit(client, h, tags["help"], body="啊")["code"] == 40000  # 太短
    assert submit(client, h, tags["help"], body="字" * 501)["code"] == 40000  # 太长
    assert submit(client, h, item_category_id)["code"] == 42291  # 物品类目不能当帖子标签
    assert submit(client, h, 99999999)["code"] == 42291
    five = {"body": "图片太多了", "tag_id": tags["help"], "images": ["/uploads/t/a.jpg"] * 5}
    assert call(client, "POST", "/posts", h, json=five)["code"] == 40000
    outside = {"body": "外链图片", "tag_id": tags["help"], "images": ["https://evil.example/a.jpg"]}
    assert call(client, "POST", "/posts", h, json=outside)["code"] == 40000


# ------------------------------------------------------------ 先审后发

def test_pending_post_is_hidden_until_approved(client, db, make_user, tags):
    author, ha = make_user(AUTHOR_NICK)
    _, hb = make_user("路人")
    admin, hadmin = make_user("管理员", role="admin")

    r = submit(client, ha, tags["lost_found"])
    assert r["code"] == 0 and r["data"]["status"] == "pending" and r["data"]["published_at"] is None
    post_id = r["data"]["id"]

    # 待审核：墙上看不到；别人打开详情是「不存在」；投稿人自己能看到
    assert post_id not in feed_ids(client, hb)
    assert call(client, "GET", f"/posts/{post_id}", hb)["code"] == 40491
    assert call(client, "GET", f"/posts/{post_id}", ha)["data"]["is_mine"] is True
    # 后台待审列表里有它
    pending = call(client, "GET", "/admin/posts", hadmin, params={"status": "pending"})["data"]["items"]
    assert post_id in [p["id"] for p in pending]

    r = approve(client, hadmin, post_id)
    assert r["code"] == 0 and r["data"]["status"] == "online" and r["data"]["published_at"] is not None
    # 通过后：上墙，别人能看详情
    assert post_id in feed_ids(client, hb)
    assert call(client, "GET", f"/posts/{post_id}", hb)["code"] == 0
    # 不能重复审核
    assert approve(client, hadmin, post_id)["code"] == 40992
    # 投稿人收到通知；管理操作写了日志
    n = db.scalar(select(Notification).where(Notification.user_id == author.id, Notification.type == "content_approved"))
    assert n is not None and n.link == f"/wall/{post_id}"
    log = db.scalar(select(AuditLog).where(AuditLog.action == "approve_post", AuditLog.target_id == post_id))
    assert log is not None and log.admin_id == admin.id


def test_reject_then_edit_and_resubmit(client, db, make_user, tags):
    author, ha = make_user(AUTHOR_NICK)
    _, hb = make_user("路人")
    _, hadmin = make_user("管理员", role="admin")
    post_id = submit(client, ha, tags["rant"], body="某某同学的宿舍号是 1-101，大家去找他")["data"]["id"]

    assert call(client, "POST", f"/admin/posts/{post_id}/reject", hadmin, json={"reason": "x"})["code"] == 40000
    r = call(client, "POST", f"/admin/posts/{post_id}/reject", hadmin, json={"reason": "包含他人隐私"})
    assert r["code"] == 0 and r["data"]["status"] == "rejected"

    # 退回原因：投稿人在「我的投稿」里能看到；别人连帖子都看不到
    mine = call(client, "GET", "/posts/mine", ha)["data"]["items"]
    assert mine[0]["id"] == post_id and mine[0]["reject_reason"] == "包含他人隐私"
    assert call(client, "GET", f"/posts/{post_id}", hb)["code"] == 40491
    assert post_id not in feed_ids(client, hb)
    n = db.scalar(select(Notification).where(Notification.user_id == author.id, Notification.type == "content_rejected"))
    assert n is not None and "包含他人隐私" in n.body and n.link == "/me/posts"

    # 修改后重新投稿：回到待审核，退回原因清空
    edited = {"body": "有同学晚上在宿舍楼道大声打电话，希望注意一下", "tag_id": tags["rant"]}
    r = call(client, "PUT", f"/posts/{post_id}", ha, json=edited)
    assert r["code"] == 0 and r["data"]["status"] == "pending" and r["data"]["reject_reason"] is None
    assert r["data"]["body"] == edited["body"]

    # 通过上墙后就不能再改了（只能撤回）
    assert approve(client, hadmin, post_id)["code"] == 0
    assert call(client, "PUT", f"/posts/{post_id}", ha, json=edited)["code"] == 40991


# ------------------------------------------------------------ 匿名

def test_author_identity_never_leaks(client, db, make_user, tags):
    author, ha = make_user(AUTHOR_NICK)
    _, hb = make_user("路人")
    _, hadmin = make_user("管理员", role="admin")
    post_id = submit(client, ha, tags["confession"], body="想认识今天在二食堂穿蓝色外套的同学")["data"]["id"]
    approve(client, hadmin, post_id)

    forbidden_keys = {"author", "owner", "owner_id", "user", "user_id", "seller", "nickname", "student_no", "avatar_url"}

    # 路人看到的墙和详情：没有任何投稿人字段，响应全文里也找不到投稿人的昵称、学号
    for resp in (
        call(client, "GET", "/posts", hb, params={"keyword": "蓝色外套"}),
        call(client, "GET", f"/posts/{post_id}", hb),
    ):
        text = json.dumps(resp, ensure_ascii=False)
        assert AUTHOR_NICK not in text and author.student_no not in text
        post = resp["data"]["items"][0] if "items" in resp["data"] else resp["data"]
        assert post["id"] == post_id
        assert not forbidden_keys & set(post)
        assert post["is_mine"] is False
        assert post["created_at"] is None  # 投稿时间也不给别人看，避免靠时间猜人

    # 投稿人自己：只知道「是我发的」，同样不带身份字段
    own = call(client, "GET", f"/posts/{post_id}", ha)["data"]
    assert own["is_mine"] is True and not forbidden_keys & set(own)

    # 管理员在后台能看到真实投稿人
    online = call(client, "GET", "/admin/posts", hadmin, params={"status": "online"})["data"]["items"]
    row = next(p for p in online if p["id"] == post_id)
    assert row["author"] == {"id": author.id, "nickname": AUTHOR_NICK, "student_no": author.student_no}

    # 管理员用普通接口看墙时，同样拿不到投稿人
    as_admin = call(client, "GET", f"/posts/{post_id}", hadmin)
    assert AUTHOR_NICK not in json.dumps(as_admin, ensure_ascii=False)


def test_post_does_not_appear_in_item_list(client, db, make_user, tags):
    """帖子和物品共用 contents 表，确认帖子不会混进物品列表（那里会显示发布者昵称）。"""
    _, ha = make_user(AUTHOR_NICK)
    _, hadmin = make_user("管理员", role="admin")
    post_id = submit(client, ha, tags["help"], body="独一无二的关键词甲乙丙 求推荐自习室")["data"]["id"]
    approve(client, hadmin, post_id)

    items = call(client, "GET", "/items", params={"keyword": "独一无二的关键词甲乙丙"})["data"]["items"]
    assert items == []
    assert call(client, "GET", f"/items/{post_id}")["code"] == 40401


# ------------------------------------------------------------ 越权与撤回

def test_only_author_can_edit_or_withdraw(client, db, make_user, tags):
    _, ha = make_user(AUTHOR_NICK)
    _, hb = make_user("路人")
    _, hadmin = make_user("管理员", role="admin")
    body = {"body": "路人想改别人的帖子", "tag_id": tags["help"]}

    pending_id = submit(client, ha, tags["help"])["data"]["id"]
    # 别人没上墙的帖子：改和撤回都按「不存在」处理，不透露它存在
    assert call(client, "PUT", f"/posts/{pending_id}", hb, json=body)["code"] == 40491
    assert call(client, "DELETE", f"/posts/{pending_id}", hb)["code"] == 40491

    online_id = submit(client, ha, tags["help"], body="第二条帖子，会被通过")["data"]["id"]
    approve(client, hadmin, online_id)
    assert call(client, "DELETE", f"/posts/{online_id}", hb)["code"] == 40391

    # 普通用户不能调用审核接口
    assert call(client, "GET", "/admin/posts", hb)["code"] == 40300
    assert approve(client, hb, pending_id)["code"] == 40300
    assert call(client, "POST", f"/admin/posts/{pending_id}/reject", hb, json={"reason": "乱来"})["code"] == 40300

    # 投稿人自己撤回：墙上消失，详情不存在，「我的投稿」里也没有了
    assert call(client, "DELETE", f"/posts/{online_id}", ha)["code"] == 0
    assert online_id not in feed_ids(client, hb)
    assert call(client, "GET", f"/posts/{online_id}", ha)["code"] == 40491
    assert online_id not in [p["id"] for p in call(client, "GET", "/posts/mine", ha)["data"]["items"]]
    # 数据还在（软删除），方便追溯
    assert db.get(Content, online_id).status == "deleted"
    # 撤回后的帖子不能再审核
    assert approve(client, hadmin, online_id)["code"] == 40491


# ------------------------------------------------------------ 限制与筛选

def test_daily_post_limit_counts_withdrawn(client, make_user, tags, monkeypatch):
    monkeypatch.setattr(settings, "WALL_DAILY_POST_LIMIT", 2)
    _, h = make_user()
    first = submit(client, h, tags["help"], body="今天第一条")["data"]["id"]
    assert submit(client, h, tags["help"], body="今天第二条")["code"] == 0
    assert submit(client, h, tags["help"], body="今天第三条")["code"] == 42991
    # 撤回一条也不能腾出名额，防止反复刷
    assert call(client, "DELETE", f"/posts/{first}", h)["code"] == 0
    assert submit(client, h, tags["help"], body="撤回后再投")["code"] == 42991


def test_feed_filter_search_and_order(client, db, make_user, tags):
    _, ha = make_user(AUTHOR_NICK)
    _, hb = make_user("路人")
    _, hadmin = make_user("管理员", role="admin")
    lost = submit(client, ha, tags["lost_found"], body="测试专用词丙丁戊 丢了一把黑色雨伞")["data"]["id"]
    buddy = submit(client, ha, tags["buddy"], body="测试专用词丙丁戊 找周末羽毛球搭子")["data"]["id"]
    # 先通过「搭子」，再通过「失物」：后上墙的排在前面，和投稿顺序无关
    approve(client, hadmin, buddy)
    approve(client, hadmin, lost)

    assert feed_ids(client, hb, keyword="测试专用词丙丁戊") == [lost, buddy]
    assert feed_ids(client, hb, keyword="测试专用词丙丁戊", tag_id=tags["buddy"]) == [buddy]
    assert feed_ids(client, hb, keyword="测试专用词丙丁戊 雨伞") == [lost]
    # 标签名也能搜到
    assert lost in feed_ids(client, hb, keyword="测试专用词丙丁戊 失物招领")

    # 置顶的排最前
    db.get(Post, buddy).pinned_at = db.get(Post, buddy).published_at
    db.flush()
    assert feed_ids(client, hb, keyword="测试专用词丙丁戊") == [buddy, lost]
