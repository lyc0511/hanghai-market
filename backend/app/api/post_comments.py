"""校园墙评论：列表、发表、回复、删除。

评论是「先发后审」：发出来立刻可见，靠敏感词拦截、举报和管理员下架来管理。

匿名规则：
    - 评论显示评论人的昵称；
    - 但帖子的投稿人（楼主）在自己帖子下评论时，一律显示为「楼主」，不返回昵称，
      发给别人的通知里也只写「楼主」——否则一条回复就把匿名破坏了。

状态（post_comments.status）：online 正常 / deleted 本人删除 / offline 管理员下架。
帖子上的 comment_count 只统计 online 的评论，增减都和评论本身在同一个事务里。

业务错误码：
    40492 评论不存在                 42292 评论包含不合适的词语
    42992 今日评论数量已达上限        40392 无权操作该评论
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.notifications import notify
from app.api.posts import lock_online_post
from app.core.banned_words import find_banned
from app.core.config import settings
from app.core.exceptions import BizError
from app.core.query import count_rows
from app.db.session import get_db
from app.models import AuditLog, Content, Post, PostComment, User
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.post import CommentCreateIn, CommentOut, CommentReplyTo

router = APIRouter(prefix="/posts", tags=["校园墙"])

LOCAL_TZ = ZoneInfo("Asia/Shanghai")
OP_NAME = "楼主"


def shown_name(user_id: int, nickname: str, owner_id: int) -> str:
    """一个评论人对外显示的名字：是楼主就显示「楼主」，否则显示昵称。"""
    return OP_NAME if user_id == owner_id else nickname


def to_out(cm: PostComment, nickname: str, owner_id: int, viewer: User, reply_to: CommentReplyTo | None) -> CommentOut:
    is_op = cm.user_id == owner_id
    return CommentOut(
        id=cm.id,
        body=cm.body,
        nickname=None if is_op else nickname,
        is_op=is_op,
        is_mine=cm.user_id == viewer.id,
        reply_to=reply_to,
        created_at=cm.created_at,
    )


def visible_post(db: Session, post_id: int, viewer: User) -> Content:
    """评论区和帖子详情的可见规则一致：已上墙的谁都能看；没上墙的只有投稿人和管理员能看。"""
    c = db.scalar(select(Content).where(Content.id == post_id, Content.type == "post"))
    if c is None or c.status == "deleted":
        raise BizError(40491, "帖子不存在")
    if c.status != "online" and not (viewer.id == c.owner_id or viewer.role == "admin"):
        raise BizError(40491, "帖子不存在")
    return c


@router.get("/{post_id}/comments", response_model=ApiResponse[Page[CommentOut]], summary="评论列表（从早到晚）")
def list_comments(
    post_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[CommentOut]]:
    c = visible_post(db, post_id, user)

    stmt = (
        select(PostComment, User.nickname)
        .join(User, User.id == PostComment.user_id)
        .where(PostComment.post_id == post_id, PostComment.status == "online")
        .order_by(PostComment.created_at, PostComment.id)
    )
    total = count_rows(db, stmt)
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()

    # 被回复的评论可能不在这一页、也可能已被删除，单独查一次它们作者的名字
    reply_ids = {cm.reply_to_id for cm, _ in rows if cm.reply_to_id}
    replied: dict[int, CommentReplyTo] = {}
    if reply_ids:
        for rid, uid, nick in db.execute(
            select(PostComment.id, PostComment.user_id, User.nickname)
            .join(User, User.id == PostComment.user_id)
            .where(PostComment.id.in_(reply_ids))
        ):
            replied[rid] = CommentReplyTo(id=rid, name=shown_name(uid, nick, c.owner_id))

    items = [to_out(cm, nick, c.owner_id, user, replied.get(cm.reply_to_id)) for cm, nick in rows]
    return ok(Page(items=items, total=total, page=page, page_size=page_size))


@router.post("/{post_id}/comments", response_model=ApiResponse[CommentOut], summary="发表评论 / 回复")
def create_comment(
    post_id: int,
    body: CommentCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[CommentOut]:
    if find_banned(body.body) is not None:
        raise BizError(42292, "评论里有不合适的词语，请修改后再发")

    today_start = datetime.combine(datetime.now(LOCAL_TZ).date(), time.min, tzinfo=LOCAL_TZ)
    commented_today = db.scalar(
        select(func.count()).select_from(PostComment).where(
            PostComment.user_id == user.id, PostComment.created_at >= today_start
        )
    )
    if commented_today >= settings.WALL_DAILY_COMMENT_LIMIT:
        raise BizError(42992, f"每天最多评论 {settings.WALL_DAILY_COMMENT_LIMIT} 条，明天再来吧")

    # 只能评论已上墙的帖子；加行锁，保证计数和评论同时成功
    c = lock_online_post(db, post_id)

    parent: PostComment | None = None
    reply_to: CommentReplyTo | None = None
    if body.reply_to_id is not None:
        parent = db.get(PostComment, body.reply_to_id)
        if parent is None or parent.post_id != post_id or parent.status != "online":
            raise BizError(40492, "要回复的评论不存在或已被删除")
        parent_nick = db.scalar(select(User.nickname).where(User.id == parent.user_id))
        reply_to = CommentReplyTo(id=parent.id, name=shown_name(parent.user_id, parent_nick, c.owner_id))

    cm = PostComment(post_id=post_id, user_id=user.id, reply_to_id=parent.id if parent else None, body=body.body)
    db.add(cm)
    db.execute(update(Post).where(Post.content_id == post_id).values(comment_count=Post.comment_count + 1))

    # 通知里显示的名字同样遵守匿名规则：楼主只显示「楼主」
    who = shown_name(user.id, user.nickname, c.owner_id)
    excerpt = body.body[:60]
    link = f"/wall/{post_id}"
    if user.id != c.owner_id:
        notify(db, c.owner_id, "post_comment", "你的投稿有新评论", f"{who}：{excerpt}", link)
    # 被回复的人：不是自己、也不是刚通知过的楼主时，再单独通知
    if parent is not None and parent.user_id not in (user.id, c.owner_id):
        notify(db, parent.user_id, "comment_reply", f"{who}回复了你的评论", f"{who}：{excerpt}", link)

    db.commit()
    db.refresh(cm)
    return ok(to_out(cm, user.nickname, c.owner_id, user, reply_to), "已发表")


@router.delete("/{post_id}/comments/{comment_id}", response_model=ApiResponse[None], summary="删除评论（本人，或管理员下架）")
def delete_comment(
    post_id: int,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    cm = db.scalar(select(PostComment).where(PostComment.id == comment_id).with_for_update())
    if cm is None or cm.post_id != post_id or cm.status != "online":
        raise BizError(40492, "评论不存在")

    is_owner = cm.user_id == user.id
    if not is_owner and user.role != "admin":
        raise BizError(40392, "无权操作该评论")

    take_comment_down(db, cm, by_admin=not is_owner)
    if not is_owner:
        notify(db, cm.user_id, "content_takedown", "你的评论已被下架", f"你的评论「{cm.body[:40]}」已被管理员下架。", f"/wall/{post_id}")
        db.add(AuditLog(admin_id=user.id, action="offline_comment", target_type="comment", target_id=cm.id))
    db.commit()
    return ok(None, "已删除" if is_owner else "已下架")


def take_comment_down(db: Session, cm: PostComment, *, by_admin: bool) -> None:
    """把一条正常的评论撤下来，并把帖子的评论数减 1。只改数据，不提交（举报处理也会调用）。"""
    cm.status = "offline" if by_admin else "deleted"
    db.execute(update(Post).where(Post.content_id == cm.post_id).values(comment_count=Post.comment_count - 1))
