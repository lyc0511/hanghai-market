"""社团活动与报名。

活动状态：
    会长发布 ──▶ pending ──管理员通过──▶ online（所有人可见、可报名）
                      └─管理员驳回──▶ rejected（会长可见驳回原因）
审核接口在 admin.py。

报名（全校同学都可以报名）：
    可以报名 = 已上架 + 还没开始 + 没过报名截止时间 + 名额没满
    取消报名：活动开始前都可以，名额退回。取消后可以再报名（复用原来那一行）。
报名和取消都先锁住活动行再改 enrolled_count：最后一个名额两人同时报名时只有一人成功。

业务错误码：
    40441 活动不存在            40341 无权查看报名名单（不是主办社团会长）
    40941 名额已满              40942 已经报名过了
    42241 活动已开始或报名已截止  42242 还没有报名
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.api.clubs import lock_club, require_president
from app.api.deps import get_current_user, get_optional_user
from app.core.constants import CampusArea
from app.core.exceptions import BizError
from app.core.query import contains, paginate
from app.db.session import get_db
from app.models import Activity, ActivitySignup, Club, Content, User
from app.schemas.activity import (
    ActivityCardOut,
    ActivityCreateIn,
    ActivityDetailOut,
    ClubBrief,
    MyActivityOut,
    SignupOut,
)
from app.schemas.common import ApiResponse, Page, ok

router = APIRouter(prefix="/activities", tags=["活动"])
club_router = APIRouter(prefix="/clubs", tags=["活动"])

When = Literal["upcoming", "ended", "all"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def phase_of(a: Activity, now: datetime) -> str:
    if now < a.start_time:
        return "upcoming"
    if now < a.end_time:
        return "ongoing"
    return "ended"


def signup_open(c: Content, a: Activity, now: datetime) -> bool:
    return (
        c.status == "online"
        and now < a.start_time
        and (a.signup_deadline is None or now <= a.signup_deadline)
        and a.enrolled_count < a.capacity
    )


def to_card(c: Content, now: datetime) -> ActivityCardOut:
    a = c.activity
    return ActivityCardOut(
        id=c.id,
        title=c.title,
        summary=c.summary,
        club=ClubBrief(id=a.club.content_id, title=a.club.content.title),
        campus_area=c.campus_area,
        location=a.location,
        start_time=a.start_time,
        end_time=a.end_time,
        signup_deadline=a.signup_deadline,
        capacity=a.capacity,
        enrolled_count=a.enrolled_count,
        phase=phase_of(a, now),
        signup_open=signup_open(c, a, now),
        status=c.status,
        tags=list(c.tags or []),
    )


def is_organizer(c: Content, viewer: User | None) -> bool:
    return viewer is not None and viewer.id == c.activity.club.president_id


def to_detail(db: Session, c: Content, viewer: User | None) -> ActivityDetailOut:
    now = now_utc()
    signed = None
    if viewer is not None:
        signed = (
            db.scalar(
                select(ActivitySignup.id).where(
                    ActivitySignup.activity_id == c.id,
                    ActivitySignup.user_id == viewer.id,
                    ActivitySignup.status == "signed",
                )
            )
            is not None
        )
    organizer = is_organizer(c, viewer)
    can_see_private = organizer or (viewer is not None and viewer.role == "admin")
    return ActivityDetailOut(
        **to_card(c, now).model_dump(),
        view_count=c.view_count,
        signed_up=signed,
        is_organizer=organizer,
        reject_reason=c.reject_reason if can_see_private else None,
        created_at=c.created_at,
    )


ACTIVITY_LOAD = (joinedload(Content.activity).joinedload(Activity.club).joinedload(Club.content),)


def with_relations(stmt):
    return stmt.options(*ACTIVITY_LOAD)


def load_activity(db: Session, activity_id: int) -> Content | None:
    return db.scalar(with_relations(select(Content).where(Content.id == activity_id, Content.type == "activity")))


def visible_activity(db: Session, activity_id: int, viewer: User | None) -> Content:
    """已上架的人人可见；待审核 / 驳回的只有主办会长和管理员能看。"""
    c = load_activity(db, activity_id)
    if c is None or c.status == "deleted":
        raise BizError(40441, "活动不存在")
    if c.status != "online" and not (is_organizer(c, viewer) or (viewer is not None and viewer.role == "admin")):
        raise BizError(40441, "活动不存在")
    return c


def page_of(db: Session, stmt, page: int, page_size: int) -> tuple[list[Content], int]:
    """活动分页：取数据时带上 活动 → 社团 → 社团内容 的预加载。"""
    return paginate(db, stmt, page, page_size, options=ACTIVITY_LOAD)


def apply_when(stmt, when: When, now: datetime):
    """upcoming：还没结束的（含进行中），按开始时间从近到远；ended：已结束的，最近结束的在前。"""
    if when == "upcoming":
        return stmt.where(Activity.end_time > now).order_by(Activity.start_time.asc(), Content.id.asc())
    if when == "ended":
        return stmt.where(Activity.end_time <= now).order_by(Activity.start_time.desc(), Content.id.desc())
    return stmt.order_by(Activity.start_time.desc(), Content.id.desc())


@router.get("", response_model=ApiResponse[Page[ActivityCardOut]], summary="活动列表（只返回已上架）")
def list_activities(
    when: When = Query(default="upcoming", description="upcoming 即将开始和进行中 / ended 已结束 / all 全部"),
    club_id: int | None = Query(default=None, description="只看某个社团的活动"),
    campus_area: CampusArea | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ActivityCardOut]]:
    now = now_utc()
    stmt = (
        select(Content)
        .join(Activity, Activity.content_id == Content.id)
        .where(Content.type == "activity", Content.status == "online")
    )
    if club_id is not None:
        stmt = stmt.where(Activity.club_id == club_id)
    if campus_area is not None:
        stmt = stmt.where(Content.campus_area == campus_area)
    if keyword:
        for word in keyword.split():
            stmt = stmt.where(Content.search_text.ilike(contains(word), escape="\\"))
    rows, total = page_of(db, apply_when(stmt, when, now), page, page_size)
    return ok(Page(items=[to_card(c, now) for c in rows], total=total, page=page, page_size=page_size))


# 注意：必须写在 /{activity_id} 前面
@router.get("/mine", response_model=ApiResponse[Page[MyActivityOut]], summary="我报名的活动")
def my_activities(
    when: When = Query(default="upcoming"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[MyActivityOut]]:
    now = now_utc()
    stmt = (
        select(Content, ActivitySignup.created_at)
        .join(Activity, Activity.content_id == Content.id)
        .join(ActivitySignup, ActivitySignup.activity_id == Content.id)
        .where(ActivitySignup.user_id == user.id, ActivitySignup.status == "signed", Content.status != "deleted")
    )
    stmt = apply_when(stmt, when, now)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(with_relations(stmt).offset((page - 1) * page_size).limit(page_size)).unique().all()
    items = [MyActivityOut(**to_card(c, now).model_dump(), signed_at=signed_at) for c, signed_at in rows]
    return ok(Page(items=items, total=int(total), page=page, page_size=page_size))


@router.get("/{activity_id}", response_model=ApiResponse[ActivityDetailOut], summary="活动详情")
def get_activity(
    activity_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ActivityDetailOut]:
    c = visible_activity(db, activity_id, viewer)
    if c.status == "online" and not is_organizer(c, viewer):
        db.execute(update(Content).where(Content.id == c.id).values(view_count=Content.view_count + 1))
        db.commit()
        c.view_count += 1
    return ok(to_detail(db, c, viewer))


def lock_activity(db: Session, activity_id: int) -> tuple[Content, Activity]:
    """锁住活动行：报名、取消都在锁里检查名额再改 enrolled_count，避免超卖。"""
    row = db.execute(
        select(Content, Activity)
        .join(Activity, Activity.content_id == Content.id)
        .where(Content.id == activity_id, Content.type == "activity")
        .with_for_update(of=Activity)
    ).one_or_none()
    if row is None or row[0].status != "online":
        raise BizError(40441, "活动不存在")
    return row[0], row[1]


@router.post("/{activity_id}/signup", response_model=ApiResponse[ActivityDetailOut], summary="报名活动")
def signup(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[ActivityDetailOut]:
    c, a = lock_activity(db, activity_id)
    now = now_utc()
    if now >= a.start_time:
        raise BizError(42241, "活动已经开始，不能再报名")
    if a.signup_deadline is not None and now > a.signup_deadline:
        raise BizError(42241, "报名已截止")

    row = db.scalar(
        select(ActivitySignup)
        .where(ActivitySignup.activity_id == a.content_id, ActivitySignup.user_id == user.id)
        .with_for_update()
    )
    if row is not None and row.status == "signed":
        raise BizError(40942, "你已经报名过了")
    if a.enrolled_count >= a.capacity:
        raise BizError(40941, "名额已满")

    if row is None:
        db.add(ActivitySignup(activity_id=a.content_id, user_id=user.id, status="signed"))
    else:
        # 取消过又重新报名：表上 (activity_id, user_id) 唯一，复用原来那一行
        row.status = "signed"
        row.created_at = now
    a.enrolled_count += 1
    db.commit()
    db.expire_all()
    return ok(to_detail(db, load_activity(db, activity_id), user), "报名成功")


@router.delete("/{activity_id}/signup", response_model=ApiResponse[ActivityDetailOut], summary="取消报名")
def cancel_signup(activity_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiResponse[ActivityDetailOut]:
    c, a = lock_activity(db, activity_id)
    if now_utc() >= a.start_time:
        raise BizError(42241, "活动已经开始，不能取消报名")
    row = db.scalar(
        select(ActivitySignup)
        .where(
            ActivitySignup.activity_id == a.content_id,
            ActivitySignup.user_id == user.id,
            ActivitySignup.status == "signed",
        )
        .with_for_update()
    )
    if row is None:
        raise BizError(42242, "你还没有报名这个活动")
    row.status = "cancelled"
    a.enrolled_count = max(0, a.enrolled_count - 1)
    db.commit()
    db.expire_all()
    return ok(to_detail(db, load_activity(db, activity_id), user), "已取消报名")


@router.get("/{activity_id}/signups", response_model=ApiResponse[Page[SignupOut]], summary="报名名单（主办会长 / 管理员）")
def list_signups(
    activity_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[SignupOut]]:
    c = visible_activity(db, activity_id, user)
    if not (is_organizer(c, user) or user.role == "admin"):
        raise BizError(40341, "只有主办社团的会长可以查看报名名单")
    stmt = (
        select(ActivitySignup, User)
        .join(User, User.id == ActivitySignup.user_id)
        .where(ActivitySignup.activity_id == c.id, ActivitySignup.status == "signed")
        .order_by(ActivitySignup.created_at.asc(), ActivitySignup.id.asc())
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    items = [SignupOut(user_id=u.id, nickname=u.nickname, avatar_url=u.avatar_url, signed_at=s.created_at) for s, u in rows]
    return ok(Page(items=items, total=int(total), page=page, page_size=page_size))


# ---------------------------------------------------------------- 社团下的活动

@club_router.get("/{club_id}/activities", response_model=ApiResponse[Page[ActivityDetailOut]], summary="某个社团的活动")
def club_activities(
    club_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ActivityDetailOut]]:
    """其他人只能看到已上架的；会长还能看到自己发布的待审核 / 被驳回的活动和驳回原因。"""
    club = db.get(Club, club_id)
    if club is None:
        raise BizError(40431, "社团不存在")
    stmt = select(Content).join(Activity, Activity.content_id == Content.id).where(Activity.club_id == club_id)
    if viewer is not None and viewer.id == club.president_id:
        stmt = stmt.where(Content.status != "deleted")
    else:
        stmt = stmt.where(Content.status == "online")
    stmt = stmt.order_by(Activity.start_time.desc(), Content.id.desc())
    rows, total = page_of(db, stmt, page, page_size)
    return ok(Page(items=[to_detail(db, c, viewer) for c in rows], total=total, page=page, page_size=page_size))


@club_router.post("/{club_id}/activities", response_model=ApiResponse[ActivityDetailOut], summary="会长发布活动（需管理员审核）")
def create_activity(
    club_id: int,
    body: ActivityCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ActivityDetailOut]:
    content, club = lock_club(db, club_id)
    require_president(club, user)
    if content.status != "online":
        raise BizError(40431, "社团不存在")
    c = Content(
        type="activity",
        owner_id=user.id,
        title=body.title,
        summary=body.summary or None,
        tags=body.tags,
        campus_area=content.campus_area,
        status="pending",
        search_text=" ".join([body.title, body.summary, body.location, content.title, *body.tags]),
        activity=Activity(
            club_id=club.content_id,
            start_time=body.start_time,
            end_time=body.end_time,
            location=body.location,
            capacity=body.capacity,
            enrolled_count=0,
            # 不填截止时间时，默认报到活动开始为止
            signup_deadline=body.signup_deadline or body.start_time,
        ),
    )
    db.add(c)
    db.commit()
    return ok(to_detail(db, load_activity(db, c.id), user), "已提交，等待管理员审核")
