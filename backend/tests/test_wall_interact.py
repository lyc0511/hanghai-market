"""校园墙互动测试：点赞、评论（楼主匿名）、已解决、举报帖子和评论、管理员下架。"""
import json

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import AuditLog, Category, Content, Notification, Post, PostComment
from tests.conftest import call

AUTHOR_NICK = "投稿人甲乙丙丁"


@pytest.fixture()
def tags(db) -> dict[str, int]:
    return {c.slug: c.id for c in db.scalars(select(Category).where(Category.type == "post"))}


@pytest.fixture()
def wall(client, db, make_user, tags):
    """准备好一条已上墙的帖子和三种角色：投稿人 a、路人 b、路人 c、管理员。"""

    class Wall:
        pass

    w = Wall()
    w.author, w.ha = make_user(AUTHOR_NICK)
    w.b, w.hb = make_user("路人小乙")
    w.c, w.hc = make_user("路人小丙")
    w.admin, w.hadmin = make_user("管理员", role="admin")
    w.tags = tags
    w.post_id = new_online_post(client, w, "在二食堂捡到一副黑框眼镜")
    return w


def new_post(client, headers, tag_id, body):
    return call(client, "POST", "/posts", headers, json={"body": body, "tag_id": tag_id})["data"]["id"]


def new_online_post(client, w, body):
    post_id = new_post(client, w.ha, w.tags["lost_found"], body)
    assert call(client, "POST", f"/admin/posts/{post_id}/approve", w.hadmin)["code"] == 0
    return post_id


def comment(client, headers, post_id, body, reply_to_id=None):
    return call(client, "POST", f"/posts/{post_id}/comments", headers, json={"body": body, "reply_to_id": reply_to_id})


def comments(client, headers, post_id):
    return call(client, "GET", f"/posts/{post_id}/comments", headers)["data"]["items"]


def post_of(client, headers, post_id):
    return call(client, "GET", f"/posts/{post_id}", headers)["data"]


def notes(db, user, ntype):
    return db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.type == ntype)).all()


# ------------------------------------------------------------ 点赞

def test_like_is_idempotent_and_per_user(client, wall):
    w = wall
    assert call(client, "POST", f"/posts/{w.post_id}/like", w.hb)["data"] == {"liked": True, "like_count": 1}
    # 重复点赞不会多算
    assert call(client, "POST", f"/posts/{w.post_id}/like", w.hb)["data"]["like_count"] == 1
    assert call(client, "POST", f"/posts/{w.post_id}/like", w.hc)["data"]["like_count"] == 2

    # 「我点过没有」是每个人各自的
    assert post_of(client, w.hb, w.post_id)["liked"] is True
    assert post_of(client, w.ha, w.post_id)["liked"] is False
    feed = call(client, "GET", "/posts", w.hb, params={"keyword": "黑框眼镜"})["data"]["items"]
    assert feed[0]["liked"] is True and feed[0]["like_count"] == 2

    assert call(client, "DELETE", f"/posts/{w.post_id}/like", w.hb)["data"] == {"liked": False, "like_count": 1}
    # 没点过再取消：不会减成负数
    assert call(client, "DELETE", f"/posts/{w.post_id}/like", w.hb)["data"]["like_count"] == 1


def test_cannot_like_or_comment_on_hidden_post(client, wall):
    w = wall
    pending = new_post(client, w.ha, w.tags["help"], "这条还在审核中")
    assert call(client, "POST", f"/posts/{pending}/like", w.hb)["code"] == 40491
    assert comment(client, w.hb, pending, "抢个沙发")["code"] == 40491
    assert call(client, "GET", f"/posts/{pending}/comments", w.hb)["code"] == 40491
    # 游客什么都做不了
    assert call(client, "GET", f"/posts/{w.post_id}/comments")["code"] == 40100
    assert call(client, "POST", f"/posts/{w.post_id}/like")["code"] == 40100


# ------------------------------------------------------------ 评论与楼主匿名

def test_op_stays_anonymous_in_comments_and_notifications(client, db, wall):
    w = wall
    # 路人 b 评论 → 投稿人收到通知
    r = comment(client, w.hb, w.post_id, "是不是镜腿有点松的那副？")
    assert r["code"] == 0 and r["data"]["nickname"] == "路人小乙" and r["data"]["is_op"] is False
    b_comment = r["data"]["id"]
    n = notes(db, w.author, "post_comment")
    assert len(n) == 1 and "路人小乙" in n[0].body and n[0].link == f"/wall/{w.post_id}"

    # 楼主回复 b：显示为「楼主」，不带昵称
    r = comment(client, w.ha, w.post_id, "对，放在一楼服务台了", reply_to_id=b_comment)
    assert r["code"] == 0
    assert r["data"]["is_op"] is True and r["data"]["nickname"] is None and r["data"]["is_mine"] is True
    assert r["data"]["reply_to"] == {"id": b_comment, "name": "路人小乙"}
    op_comment = r["data"]["id"]

    # b 收到的通知里只有「楼主」，没有投稿人的昵称
    n = notes(db, w.b, "comment_reply")
    assert len(n) == 1 and n[0].title == "楼主回复了你的评论"
    assert AUTHOR_NICK not in n[0].title + n[0].body

    # 路人 c 回复楼主的评论：被回复者显示为「楼主」
    r = comment(client, w.hc, w.post_id, "谢谢楼主", reply_to_id=op_comment)
    assert r["data"]["reply_to"] == {"id": op_comment, "name": "楼主"}
    # 楼主既是帖子主人又是被回复的人：只通知一次
    assert len(notes(db, w.author, "post_comment")) == 2
    assert notes(db, w.author, "comment_reply") == []

    # 路人看到的评论区：全文找不到投稿人的昵称和学号
    resp = call(client, "GET", f"/posts/{w.post_id}/comments", w.hc)
    text = json.dumps(resp, ensure_ascii=False)
    assert AUTHOR_NICK not in text and w.author.student_no not in text
    items = resp["data"]["items"]
    assert [c["nickname"] for c in items] == ["路人小乙", None, "路人小丙"]
    assert [c["is_op"] for c in items] == [False, True, False]
    assert [c["is_mine"] for c in items] == [False, False, True]
    assert not {"user_id", "author", "student_no"} & set(items[0])

    assert post_of(client, w.hc, w.post_id)["comment_count"] == 3


def test_comment_rules(client, wall, monkeypatch):
    w = wall
    assert comment(client, w.hb, w.post_id, "   ")["code"] == 40000
    assert comment(client, w.hb, w.post_id, "字" * 301)["code"] == 40000
    # 敏感词：直接写、用空格隔开都会被拦
    assert comment(client, w.hb, w.post_id, "需要代考的联系我")["code"] == 42292
    assert comment(client, w.hb, w.post_id, "需要 代 考 的联系我")["code"] == 42292
    assert post_of(client, w.hb, w.post_id)["comment_count"] == 0

    # 不能回复别的帖子下的评论
    other_post = new_online_post(client, w, "另一条帖子")
    other_comment = comment(client, w.hb, other_post, "这是另一条帖子的评论")["data"]["id"]
    assert comment(client, w.hc, w.post_id, "串台回复", reply_to_id=other_comment)["code"] == 40492
    assert comment(client, w.hc, w.post_id, "回复不存在的评论", reply_to_id=99999999)["code"] == 40492

    # 每日上限（b 今天已经成功评论 1 条）
    monkeypatch.setattr(settings, "WALL_DAILY_COMMENT_LIMIT", 2)
    assert comment(client, w.hb, w.post_id, "第二条")["code"] == 0
    assert comment(client, w.hb, w.post_id, "第三条")["code"] == 42992


def test_delete_comment_by_owner_and_admin(client, db, wall):
    w = wall
    first = comment(client, w.hb, w.post_id, "第一条评论")["data"]["id"]
    second = comment(client, w.hc, w.post_id, "第二条评论")["data"]["id"]
    assert post_of(client, w.ha, w.post_id)["comment_count"] == 2

    # 别人不能删；楼主也不能删别人的评论（只能举报）
    assert call(client, "DELETE", f"/posts/{w.post_id}/comments/{first}", w.hc)["code"] == 40392
    assert call(client, "DELETE", f"/posts/{w.post_id}/comments/{first}", w.ha)["code"] == 40392

    # 本人删除：评论消失，计数减 1，不能再回复它
    assert call(client, "DELETE", f"/posts/{w.post_id}/comments/{first}", w.hb)["code"] == 0
    assert [c["id"] for c in comments(client, w.ha, w.post_id)] == [second]
    assert post_of(client, w.ha, w.post_id)["comment_count"] == 1
    assert comment(client, w.ha, w.post_id, "回复已删除的评论", reply_to_id=first)["code"] == 40492
    assert call(client, "DELETE", f"/posts/{w.post_id}/comments/{first}", w.hb)["code"] == 40492

    # 管理员下架：通知评论人，写操作日志
    assert call(client, "DELETE", f"/posts/{w.post_id}/comments/{second}", w.hadmin)["code"] == 0
    assert comments(client, w.ha, w.post_id) == []
    assert post_of(client, w.ha, w.post_id)["comment_count"] == 0
    assert db.get(PostComment, second).status == "offline" and db.get(PostComment, first).status == "deleted"
    assert len(notes(db, w.c, "content_takedown")) == 1
    assert db.scalar(select(AuditLog).where(AuditLog.action == "offline_comment", AuditLog.target_id == second)) is not None


# ------------------------------------------------------------ 已解决

def test_resolve_only_by_author(client, wall):
    w = wall
    assert call(client, "POST", f"/posts/{w.post_id}/resolve", w.hb)["code"] == 40391
    r = call(client, "POST", f"/posts/{w.post_id}/resolve", w.ha)
    assert r["code"] == 0 and r["data"]["resolved"] is True
    assert post_of(client, w.hb, w.post_id)["resolved"] is True
    assert call(client, "DELETE", f"/posts/{w.post_id}/resolve", w.ha)["data"]["resolved"] is False
    # 没上墙的帖子不能标记
    pending = new_post(client, w.ha, w.tags["help"], "还在审核的帖子")
    assert call(client, "POST", f"/posts/{pending}/resolve", w.ha)["code"] == 40991


# ------------------------------------------------------------ 举报

def test_report_post_and_take_down(client, db, wall):
    w = wall
    body = {"target_type": "post", "target_id": w.post_id, "reason": "privacy"}
    assert call(client, "POST", "/reports", w.ha, json=body)["code"] == 42251  # 不能举报自己的
    r = call(client, "POST", "/reports", w.hb, json=body)
    assert r["code"] == 0 and r["data"]["target"]["type"] == "post" and r["data"]["target"]["link"] == f"/wall/{w.post_id}"
    report_id = r["data"]["id"]
    assert call(client, "POST", "/reports", w.hb, json=body)["code"] == 40951  # 不能重复举报

    # 举报人在「我的举报」里看不到投稿人是谁
    mine = call(client, "GET", "/reports/mine", w.hb)
    assert AUTHOR_NICK not in json.dumps(mine, ensure_ascii=False)
    # 管理员能看到投稿人
    rows = call(client, "GET", "/admin/reports", w.hadmin, params={"target_type": "post"})["data"]["items"]
    row = next(x for x in rows if x["id"] == report_id)
    assert row["owner"]["nickname"] == AUTHOR_NICK

    handle = {"action": "resolve", "note": "确实包含他人信息", "takedown": True}
    assert call(client, "POST", f"/admin/reports/{report_id}/handle", w.hadmin, json=handle)["code"] == 0
    # 帖子下架：墙上消失，别人打不开；投稿人自己还能看到，并收到通知
    assert db.get(Content, w.post_id).status == "offline"
    assert call(client, "GET", f"/posts/{w.post_id}", w.hb)["code"] == 40491
    assert post_of(client, w.ha, w.post_id)["status"] == "offline"
    n = notes(db, w.author, "content_takedown")
    assert len(n) == 1 and n[0].link == f"/wall/{w.post_id}" and "泄露隐私" in n[0].body
    assert len(notes(db, w.b, "report_resolved")) == 1


def test_report_comment_and_take_down(client, db, wall):
    w = wall
    cm = comment(client, w.hb, w.post_id, "这条评论会被举报")["data"]["id"]
    body = {"target_type": "comment", "target_id": cm, "reason": "abuse"}
    assert call(client, "POST", "/reports", w.hb, json=body)["code"] == 42251  # 不能举报自己的评论
    r = call(client, "POST", "/reports", w.hc, json=body)
    assert r["code"] == 0
    assert r["data"]["target"] == {
        "type": "comment", "id": cm, "title": "这条评论会被举报", "status": "online", "link": f"/wall/{w.post_id}",
    }
    report_id = r["data"]["id"]

    rows = call(client, "GET", "/admin/reports", w.hadmin, params={"target_type": "comment"})["data"]["items"]
    assert next(x for x in rows if x["id"] == report_id)["owner"]["nickname"] == "路人小乙"

    handle = {"action": "resolve", "note": "言语不当", "takedown": True}
    r = call(client, "POST", f"/admin/reports/{report_id}/handle", w.hadmin, json=handle)
    assert r["code"] == 0 and r["data"]["target"]["status"] == "offline"
    assert comments(client, w.ha, w.post_id) == []
    assert db.get(Post, w.post_id).comment_count == 0
    assert len(notes(db, w.b, "content_takedown")) == 1
    # 帖子本身不受影响
    assert db.get(Content, w.post_id).status == "online"


# ------------------------------------------------------------ 管理员直接下架

def test_admin_takes_post_offline(client, db, wall):
    w = wall
    url = f"/admin/posts/{w.post_id}/offline"
    assert call(client, "POST", url, w.hb, json={"reason": "我看不顺眼"})["code"] == 40300
    r = call(client, "POST", url, w.hadmin, json={"reason": "过审后被发现包含联系方式"})
    assert r["code"] == 0 and r["data"]["status"] == "offline"
    assert call(client, "POST", url, w.hadmin, json={"reason": "再下架一次"})["code"] == 40991

    assert call(client, "GET", f"/posts/{w.post_id}", w.hb)["code"] == 40491
    mine = call(client, "GET", "/posts/mine", w.ha, params={"status": "offline"})["data"]["items"]
    assert mine[0]["id"] == w.post_id and mine[0]["reject_reason"] == "过审后被发现包含联系方式"
    assert len(notes(db, w.author, "content_takedown")) == 1
    assert db.scalar(select(AuditLog).where(AuditLog.action == "offline_post", AuditLog.target_id == w.post_id)) is not None
