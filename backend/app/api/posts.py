"""校园墙：投稿、信息流、我的投稿、详情、修改后重投、撤回；管理员审核。

模式是「投稿墙」：任何登录用户都能投稿，管理员审核通过后才上墙（先审后发）。

状态流转（存在 contents.status）：
    投稿 ──▶ pending ──通过──▶ online（上墙）
                └──退回──▶ rejected ──投稿人修改──▶ pending
    投稿人撤回：pending / online / rejected ──▶ deleted（软删除）
已上墙的帖子不能修改，只能撤回：防止「先发正常内容过审，再改成违规内容」。

匿名规则（最重要）：
    - 面向普通用户的接口一律返回 PostOut，其中没有投稿人的任何字段；
    - 「是不是我发的」由服务器比较后只返回 is_mine（是 / 否）；
    - 只有 /admin/posts 下的管理员接口返回投稿人；
    - 看墙必须登录（游客看不到帖子内容）。

业务错误码：
    40491 帖子不存在                 42291 标签不存在
    42991 今日投稿数量已达上限        40391 无权操作该帖子
    40991 帖子当前状态不能执行此操作   40992 帖子当前状态不能审核
（评论的接口和错误码见 post_comments.py）
"""
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.api import post_ai
from app.api.deps import get_current_user, require_admin
from app.api.notifications import notify
from app.api.upload import public_url
from app.core.config import settings
from app.core.exceptions import BizError
from app.core.query import contains, paginate
from app.db.session import get_db
from app.models import AuditLog, Category, Content, Post, PostLike, User
from app.schemas.admin import RejectIn
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.post import (
    AdminPostOut, LikeOut, OfficialPostIn, PostAuthor, PostCreateIn, PostOut, PostStatus, PostTag, TagCount, WallSummaryOut,
)

router = APIRouter(prefix="/posts", tags=["校园墙"])
admin_router = APIRouter(prefix="/admin/posts", tags=["管理后台"])

# 「每天」按北京时间零点切分
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

# 普通接口取帖子时一起加载：帖子详情、标签。故意不加载 owner（投稿人）
POST_LOAD = (joinedload(Content.post), joinedload(Content.category))
# 管理员接口额外加载投稿人
ADMIN_LOAD = (*POST_LOAD, joinedload(Content.owner))

STATUS_LABELS = {"pending": "待审核", "online": "已上墙", "offline": "已下架", "rejected": "已退回", "deleted": "已撤回"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_title(body: str) -> str:
    """contents.title 必填，帖子没有标题：取正文第一行的前 40 个字，用在通知和后台列表里。"""
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    return first_line[:40]


def build_search_text(body: str, tag_name: str) -> str:
    return f"{body} {tag_name}"


def _base_fields(c: Content, viewer: User, liked: bool = False) -> dict[str, Any]:
    is_mine = viewer.id == c.owner_id
    can_see_private = is_mine or viewer.role == "admin"
    p = c.post
    return dict(
        id=c.id,
        body=p.body,
        images=[public_url(path) for path in p.images],
        tag=PostTag(id=c.category.id, name=c.category.name, slug=c.category.slug) if c.category else None,
        status=c.status,
        is_mine=is_mine,
        is_official=p.is_official,
        pinned=p.pinned_at is not None,
        resolved=p.resolved_at is not None,
        like_count=p.like_count,
        liked=liked,
        comment_count=p.comment_count,
        published_at=p.published_at,
        created_at=c.created_at if can_see_private else None,
        reject_reason=c.reject_reason if can_see_private else None,
    )


def to_out(c: Content, viewer: User, liked: bool = False) -> PostOut:
    return PostOut(**_base_fields(c, viewer, liked))


def liked_ids(db: Session, user_id: int, post_ids: list[int]) -> set[int]:
    """这批帖子里，当前用户点过赞的有哪些。一页只查一次，不逐条查。"""
    if not post_ids:
        return set()
    return set(db.scalars(select(PostLike.post_id).where(PostLike.user_id == user_id, PostLike.post_id.in_(post_ids))))


def to_out_list(db: Session, rows: list[Content], viewer: User) -> list[PostOut]:
    liked = liked_ids(db, viewer.id, [c.id for c in rows])
    return [to_out(c, viewer, c.id in liked) for c in rows]


def to_admin_out(c: Content, admin: User) -> AdminPostOut:
    return AdminPostOut(
        **_base_fields(c, admin),
        author=PostAuthor(id=c.owner.id, nickname=c.owner.nickname, student_no=c.owner.student_no),
        ai_level=c.post.ai_level,
        ai_note=c.post.ai_note,
    )


def load_post(db: Session, post_id: int, options: tuple = POST_LOAD) -> Content | None:
    return db.scalar(select(Content).where(Content.id == post_id, Content.type == "post").options(*options))


def get_tag(db: Session, tag_id: int) -> Category:
    tag = db.get(Category, tag_id)
    if tag is None or tag.type != "post":
        raise BizError(42291, "标签不存在")
    return tag


# ---------------------------------------------------------------- 投稿与浏览

@router.post("", response_model=ApiResponse[PostOut], summary="投稿（提交后待审核）")
def create_post(
    body: PostCreateIn,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PostOut]:
    tag = get_tag(db, body.tag_id)

    today_start = datetime.combine(datetime.now(LOCAL_TZ).date(), time.min, tzinfo=LOCAL_TZ)
    posted_today = db.scalar(
        select(func.count())
        .select_from(Content)
        .where(Content.owner_id == user.id, Content.type == "post", Content.created_at >= today_start)
    )
    if posted_today >= settings.WALL_DAILY_POST_LIMIT:
        raise BizError(42991, f"每天最多投稿 {settings.WALL_DAILY_POST_LIMIT} 条，明天再来吧")

    # contents 和 posts 两行在同一个事务里写入
    content = Content(
        type="post",
        owner_id=user.id,
        title=make_title(body.body),
        summary=body.body[:300],
        category_id=tag.id,
        status="pending",
        search_text=build_search_text(body.body, tag.name),
        post=Post(body=body.body, images=body.images),
    )
    db.add(content)
    db.commit()
    # AI 预审放到后台做：接口先返回，不让投稿人等大模型
    background.add_task(post_ai.prescreen_in_background, content.id)
    return ok(to_out(load_post(db, content.id), user), "投稿成功，审核通过后会通知你")


@router.get("", response_model=ApiResponse[Page[PostOut]], summary="墙：信息流（只有已上墙的，需登录）")
def list_posts(
    tag_id: int | None = Query(default=None, description="按标签筛选"),
    keyword: str | None = Query(default=None, max_length=50, description="关键词，空格分隔多个词，需全部命中"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[PostOut]]:
    stmt = select(Content).join(Post, Post.content_id == Content.id).where(
        Content.type == "post", Content.status == "online"
    )
    if tag_id is not None:
        stmt = stmt.where(Content.category_id == tag_id)
    if keyword:
        for word in keyword.split():
            stmt = stmt.where(Content.search_text.ilike(contains(word), escape="\\"))
    # 置顶的在最前，其余按上墙时间从新到旧
    stmt = stmt.order_by(Post.pinned_at.desc().nulls_last(), Post.published_at.desc().nulls_last(), Content.id.desc())

    rows, total = paginate(db, stmt, page, page_size, options=POST_LOAD)
    return ok(Page(items=to_out_list(db, rows, user), total=total, page=page, page_size=page_size))


# 注意：/summary 和 /mine 都必须写在 /{post_id} 前面，否则会被当成帖子 id 去匹配
@router.get("/summary", response_model=ApiResponse[WallSummaryOut], summary="墙的统计数字（游客可见，不含任何帖子内容）")
def wall_summary(db: Session = Depends(get_db)) -> ApiResponse[WallSummaryOut]:
    online = (Content.type == "post", Content.status == "online")
    today_start = datetime.combine(datetime.now(LOCAL_TZ).date(), time.min, tzinfo=LOCAL_TZ)
    total = db.scalar(select(func.count()).select_from(Content).where(*online)) or 0
    today = db.scalar(
        select(func.count()).select_from(Content).join(Post, Post.content_id == Content.id)
        .where(*online, Post.published_at >= today_start)
    ) or 0
    # 每个标签都列出来，没有帖子的显示 0
    counts = dict(db.execute(select(Content.category_id, func.count()).where(*online).group_by(Content.category_id)).all())
    tags = db.scalars(select(Category).where(Category.type == "post").order_by(Category.sort_order, Category.id)).all()
    return ok(WallSummaryOut(
        today=int(today), total=int(total),
        tags=[TagCount(name=t.name, slug=t.slug, count=int(counts.get(t.id, 0))) for t in tags],
    ))


@router.get("/mine", response_model=ApiResponse[Page[PostOut]], summary="我的投稿（含待审核、已退回）")
def list_my_posts(
    status: PostStatus | None = Query(default=None, description="不传返回全部"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[PostOut]]:
    stmt = select(Content).where(Content.type == "post", Content.owner_id == user.id, Content.status != "deleted")
    if status is not None:
        stmt = stmt.where(Content.status == status)
    stmt = stmt.order_by(Content.created_at.desc(), Content.id.desc())

    rows, total = paginate(db, stmt, page, page_size, options=POST_LOAD)
    return ok(Page(items=to_out_list(db, rows, user), total=total, page=page, page_size=page_size))


@router.get("/{post_id}", response_model=ApiResponse[PostOut], summary="帖子详情（需登录）")
def get_post(
    post_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PostOut]:
    c = load_post(db, post_id)
    if c is None or c.status == "deleted":
        raise BizError(40491, "帖子不存在")
    # 没上墙的帖子（待审核 / 被退回 / 被下架）只有投稿人本人和管理员能看，对其他人按「不存在」处理
    if c.status != "online" and not (user.id == c.owner_id or user.role == "admin"):
        raise BizError(40491, "帖子不存在")

    if c.status == "online" and user.id != c.owner_id:
        db.execute(update(Content).where(Content.id == c.id).values(view_count=Content.view_count + 1))
        db.commit()
    return ok(to_out(c, user, c.id in liked_ids(db, user.id, [c.id])))


# ---------------------------------------------------------------- 投稿人管理自己的帖子

def lock_own_post(db: Session, post_id: int, user: User) -> Content:
    """加行锁取出帖子，并确认是本人的、未撤回的帖子。"""
    c = db.scalar(select(Content).where(Content.id == post_id, Content.type == "post").with_for_update())
    if c is None or c.status == "deleted":
        raise BizError(40491, "帖子不存在")
    if c.owner_id != user.id:
        # 别人没上墙的帖子，连「存在」都不透露
        if c.status == "online":
            raise BizError(40391, "无权操作该帖子")
        raise BizError(40491, "帖子不存在")
    return c


@router.put("/{post_id}", response_model=ApiResponse[PostOut], summary="修改后重新投稿（仅待审核 / 已退回）")
def update_post(
    post_id: int,
    body: PostCreateIn,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PostOut]:
    c = lock_own_post(db, post_id, user)
    if c.status not in ("pending", "rejected"):
        raise BizError(40991, f"帖子当前状态为「{STATUS_LABELS.get(c.status, c.status)}」，不能修改；如需更改请撤回后重新投稿")
    tag = get_tag(db, body.tag_id)

    post = db.get(Post, c.id)
    c.title = make_title(body.body)
    c.summary = body.body[:300]
    c.category_id = tag.id
    c.search_text = build_search_text(body.body, tag.name)
    c.status = "pending"
    c.reject_reason = None
    post.body = body.body
    post.images = body.images
    # 内容变了，之前的 AI 预审结果作废
    post.ai_level = None
    post.ai_note = None
    db.commit()
    db.expire_all()
    background.add_task(post_ai.prescreen_in_background, post_id)
    return ok(to_out(load_post(db, post_id), user), "已重新提交，审核通过后会通知你")


@router.delete("/{post_id}", response_model=ApiResponse[None], summary="撤回帖子（软删除）")
def withdraw_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[None]:
    c = lock_own_post(db, post_id, user)
    # 软删除：只改状态，数据保留，出了纠纷还能追溯
    c.status = "deleted"
    db.commit()
    return ok(None, "已撤回")


# ---------------------------------------------------------------- 点赞与「已解决」

def lock_online_post(db: Session, post_id: int) -> Content:
    """取出已上墙的帖子并加行锁；没上墙的一律按「不存在」处理。"""
    c = db.scalar(select(Content).where(Content.id == post_id, Content.type == "post").with_for_update())
    if c is None or c.status != "online":
        raise BizError(40491, "帖子不存在")
    return c


def like_result(db: Session, post_id: int, liked: bool) -> LikeOut:
    return LikeOut(liked=liked, like_count=db.scalar(select(Post.like_count).where(Post.content_id == post_id)))


@router.post("/{post_id}/like", response_model=ApiResponse[LikeOut], summary="点赞（重复点不会多算）")
def like_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[LikeOut]:
    lock_online_post(db, post_id)
    # 联合主键 + ON CONFLICT DO NOTHING：已经点过就什么都不做。
    # 用 RETURNING 判断是否真的新增了一行（受影响行数在这种写法下不可靠），只有新增时才给计数 +1
    inserted = db.execute(
        pg_insert(PostLike).values(post_id=post_id, user_id=user.id).on_conflict_do_nothing().returning(PostLike.post_id)
    ).first()
    if inserted is not None:
        db.execute(update(Post).where(Post.content_id == post_id).values(like_count=Post.like_count + 1))
    db.commit()
    return ok(like_result(db, post_id, True))


@router.delete("/{post_id}/like", response_model=ApiResponse[LikeOut], summary="取消点赞")
def unlike_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[LikeOut]:
    lock_online_post(db, post_id)
    removed = db.execute(
        delete(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user.id).returning(PostLike.post_id)
    ).first()
    if removed is not None:
        db.execute(update(Post).where(Post.content_id == post_id).values(like_count=Post.like_count - 1))
    db.commit()
    return ok(like_result(db, post_id, False))


def set_resolved(db: Session, post_id: int, user: User, resolved: bool) -> PostOut:
    c = lock_own_post(db, post_id, user)
    if c.status != "online":
        raise BizError(40991, "只有已上墙的帖子可以标记")
    db.get(Post, c.id).resolved_at = now_utc() if resolved else None
    db.commit()
    db.expire_all()
    return to_out(load_post(db, post_id), user, post_id in liked_ids(db, user.id, [post_id]))


@router.post("/{post_id}/resolve", response_model=ApiResponse[PostOut], summary="标记为已解决（投稿人）")
def resolve_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[PostOut]:
    return ok(set_resolved(db, post_id, user, True), "已标记为已解决")


@router.delete("/{post_id}/resolve", response_model=ApiResponse[PostOut], summary="取消已解决标记（投稿人）")
def unresolve_post(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[PostOut]:
    return ok(set_resolved(db, post_id, user, False), "已取消标记")


# ---------------------------------------------------------------- 管理员审核

@admin_router.get("", response_model=ApiResponse[Page[AdminPostOut]], summary="墙审核列表（含投稿人和 AI 预审结果）")
def list_posts_for_review(
    status: PostStatus = Query(default="pending", description="按状态筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[AdminPostOut]]:
    stmt = select(Content).where(Content.type == "post", Content.status == status)
    # 待审核按投稿时间从早到晚，先来先审；其他状态最新的在前
    order = Content.created_at.asc() if status == "pending" else Content.created_at.desc()
    rows, total = paginate(db, stmt.order_by(order, Content.id), page, page_size, options=ADMIN_LOAD)
    return ok(Page(items=[to_admin_out(c, admin) for c in rows], total=total, page=page, page_size=page_size))


def lock_pending_post(db: Session, post_id: int) -> Content:
    """取出帖子并加行锁。两个管理员同时审核同一条时，后到的会等前一个提交，再看到最新状态。"""
    c = db.scalar(select(Content).where(Content.id == post_id, Content.type == "post").with_for_update())
    if c is None or c.status == "deleted":
        raise BizError(40491, "帖子不存在")
    if c.status != "pending":
        raise BizError(40992, f"该帖子当前状态为「{STATUS_LABELS.get(c.status, c.status)}」，不能审核")
    return c


def reload_for_admin(db: Session, post_id: int, admin: User) -> AdminPostOut:
    db.expire_all()  # 提交后重新读取，确保返回的是数据库里的最新数据
    return to_admin_out(load_post(db, post_id, ADMIN_LOAD), admin)


@admin_router.post("/{post_id}/approve", response_model=ApiResponse[AdminPostOut], summary="审核通过（上墙）")
def approve_post(
    post_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminPostOut]:
    c = lock_pending_post(db, post_id)
    c.status = "online"
    c.reject_reason = None
    db.get(Post, c.id).published_at = now_utc()
    notify(db, c.owner_id, "content_approved", "投稿已上墙", f"你的投稿「{c.title}」已通过审核，现在大家都能看到了。", f"/wall/{c.id}")
    db.add(AuditLog(admin_id=admin.id, action="approve_post", target_type="post", target_id=c.id))
    db.commit()
    return ok(reload_for_admin(db, post_id, admin), "已通过，帖子已上墙")


@admin_router.post("/{post_id}/reject", response_model=ApiResponse[AdminPostOut], summary="审核退回（附原因）")
def reject_post(
    post_id: int,
    body: RejectIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminPostOut]:
    c = lock_pending_post(db, post_id)
    c.status = "rejected"
    c.reject_reason = body.reason
    notify(
        db, c.owner_id, "content_rejected", "投稿未通过审核",
        f"你的投稿「{c.title}」未通过审核：{body.reason}。可以修改后重新投稿。", "/me/posts",
    )
    db.add(AuditLog(
        admin_id=admin.id, action="reject_post", target_type="post", target_id=c.id, detail={"reason": body.reason}
    ))
    db.commit()
    return ok(reload_for_admin(db, post_id, admin), "已退回")


@admin_router.post("/{post_id}/offline", response_model=ApiResponse[AdminPostOut], summary="下架已上墙的帖子（附原因）")
def take_post_offline(
    post_id: int,
    body: RejectIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminPostOut]:
    c = db.scalar(select(Content).where(Content.id == post_id, Content.type == "post").with_for_update())
    if c is None or c.status == "deleted":
        raise BizError(40491, "帖子不存在")
    if c.status != "online":
        raise BizError(40991, f"该帖子当前状态为「{STATUS_LABELS.get(c.status, c.status)}」，不能下架")
    c.status = "offline"
    c.reject_reason = body.reason
    notify(db, c.owner_id, "content_takedown", "你的帖子已被下架", f"你的投稿「{c.title}」已被管理员下架：{body.reason}", f"/wall/{c.id}")
    db.add(AuditLog(
        admin_id=admin.id, action="offline_post", target_type="post", target_id=c.id, detail={"reason": body.reason}
    ))
    db.commit()
    return ok(reload_for_admin(db, post_id, admin), "已下架")


# ---------------------------------------------------------------- 官方帖与置顶

@admin_router.post("", response_model=ApiResponse[AdminPostOut], summary="发布官方帖（不用审核，直接上墙）")
def create_official_post(
    body: OfficialPostIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminPostOut]:
    tag = get_tag(db, body.tag_id)
    now = now_utc()
    content = Content(
        type="post",
        owner_id=admin.id,
        title=make_title(body.body),
        summary=body.body[:300],
        category_id=tag.id,
        status="online",
        search_text=build_search_text(body.body, tag.name),
        post=Post(body=body.body, images=body.images, is_official=True, published_at=now, pinned_at=now if body.pinned else None),
    )
    db.add(content)
    db.flush()
    db.add(AuditLog(
        admin_id=admin.id, action="official_post", target_type="post", target_id=content.id, detail={"pinned": body.pinned}
    ))
    db.commit()
    return ok(reload_for_admin(db, content.id, admin), "已发布")


def set_pinned(db: Session, post_id: int, admin: User, pinned: bool) -> AdminPostOut:
    c = db.scalar(select(Content).where(Content.id == post_id, Content.type == "post").with_for_update())
    if c is None or c.status == "deleted":
        raise BizError(40491, "帖子不存在")
    if c.status != "online":
        raise BizError(40991, "只有已上墙的帖子可以置顶")
    db.get(Post, c.id).pinned_at = now_utc() if pinned else None
    db.add(AuditLog(admin_id=admin.id, action="pin_post" if pinned else "unpin_post", target_type="post", target_id=c.id))
    db.commit()
    return reload_for_admin(db, post_id, admin)


@admin_router.post("/{post_id}/pin", response_model=ApiResponse[AdminPostOut], summary="置顶帖子")
def pin_post(post_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> ApiResponse[AdminPostOut]:
    return ok(set_pinned(db, post_id, admin, True), "已置顶")


@admin_router.delete("/{post_id}/pin", response_model=ApiResponse[AdminPostOut], summary="取消置顶")
def unpin_post(post_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> ApiResponse[AdminPostOut]:
    return ok(set_pinned(db, post_id, admin, False), "已取消置顶")
