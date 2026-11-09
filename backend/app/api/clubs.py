"""社团目录与入社。

招新是否开放，要同时满足：recruit_status = recruiting，且今天（北京时间）落在起止日期内。

入社申请：
    未加入 ──提交──▶ pending ──会长通过──▶ approved（写入 club_members，member_count + 1）
                     └─会长拒绝──▶ rejected（可以再次申请，会新插入一行）
成员退出：删除 club_members 一行，member_count - 1。会长不能退出。

业务错误码：
    40431 社团不存在                 40432 入社申请不存在
    40331 无权管理该社团（不是会长）
    40931 已是成员                   40932 已有待审申请
    40933 申请当前状态不能审批
    42231 当前不在招新               42232 会长不能退出
    42233 还不是该社团成员
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_optional_user
from app.api.intents import notify
from app.api.meta import ENUMS
from app.api.upload import public_url
from app.core.constants import CampusArea
from app.core.exceptions import BizError
from app.db.session import get_db
from app.models import Club, ClubApplication, ClubMember, Content, User
from app.schemas.club import (
    ApplicationCreateIn,
    ApplicationOut,
    ApplicationRejectIn,
    ApplicationStatus,
    ClubCardOut,
    ClubDetailOut,
    ClubType,
    ClubUpdateIn,
    MemberOut,
    MyApplicationOut,
    MyClubOut,
    MyStatus,
    UserBrief,
)
from app.schemas.common import ApiResponse, Page, ok

router = APIRouter(prefix="/clubs", tags=["社团"])
application_router = APIRouter(prefix="/club-applications", tags=["社团"])

LOCAL_TZ = ZoneInfo("Asia/Shanghai")
# 种子数据用这两个词标记招新状态，会长改招新开关时同步换掉，避免搜索和标签对不上
STATUS_TAGS = {"招新中", "社团"}


def shanghai_today() -> date:
    return datetime.now(LOCAL_TZ).date()


def escape_like(s: str) -> str:
    """转义 LIKE 通配符，让用户输入的 % 和 _ 按普通字符匹配。"""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def is_recruiting(club: Club, today: date) -> bool:
    if club.recruit_status != "recruiting":
        return False
    if club.recruit_start is not None and today < club.recruit_start:
        return False
    if club.recruit_end is not None and today > club.recruit_end:
        return False
    return True


def recruiting_sql(today: date):
    """和 is_recruiting 同一套规则，用在列表筛选和排序里。"""
    return and_(
        Club.recruit_status == "recruiting",
        or_(Club.recruit_start.is_(None), Club.recruit_start <= today),
        or_(Club.recruit_end.is_(None), Club.recruit_end >= today),
    )


def logo_of(path: str | None) -> str | None:
    if not path:
        return None
    return public_url(path) if path.startswith("/uploads/") else path


def build_search_text(title: str, summary: str | None, note: str | None, tags: list[str]) -> str:
    return " ".join([title, summary or "", note or "", *tags])


def page_rows(db: Session, stmt, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return rows, int(total)


def load_club(db: Session, club_id: int) -> Content | None:
    return db.scalar(
        select(Content)
        .where(Content.id == club_id, Content.type == "club")
        .options(joinedload(Content.club).joinedload(Club.president))
    )


def lock_club(db: Session, club_id: int) -> tuple[Content, Club]:
    """锁住社团和它的内容行，再改成员数或招新信息，避免并发把 member_count 加错。"""
    row = db.execute(
        select(Content, Club)
        .join(Club, Club.content_id == Content.id)
        .where(Content.id == club_id, Content.type == "club")
        .with_for_update(of=[Content, Club])
    ).one_or_none()
    if row is None or row[0].status == "deleted":
        raise BizError(40431, "社团不存在")
    return row[0], row[1]


def require_president(club: Club, user: User) -> None:
    if club.president_id != user.id:
        raise BizError(40331, "只有会长可以管理这个社团")


def visible_club(db: Session, club_id: int, viewer: User | None) -> Content:
    content = load_club(db, club_id)
    if content is None or content.club is None or content.status == "deleted":
        raise BizError(40431, "社团不存在")
    if content.status != "online":
        allowed = viewer is not None and (viewer.role == "admin" or viewer.id == content.club.president_id)
        if not allowed:
            raise BizError(40431, "社团不存在")
    return content


def my_status_of(db: Session, club: Club, viewer: User | None) -> MyStatus | None:
    if viewer is None:
        return None
    if viewer.id == club.president_id:
        return "president"
    role = db.scalar(
        select(ClubMember.role).where(ClubMember.club_id == club.content_id, ClubMember.user_id == viewer.id)
    )
    if role == "president":
        return "president"
    if role == "member":
        return "member"
    pending = db.scalar(
        select(ClubApplication.id).where(
            ClubApplication.club_id == club.content_id,
            ClubApplication.user_id == viewer.id,
            ClubApplication.status == "pending",
        )
    )
    return "pending" if pending is not None else "none"


def pending_count_of(db: Session, club_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(ClubApplication)
            .where(ClubApplication.club_id == club_id, ClubApplication.status == "pending")
        )
        or 0
    )


def to_card(content: Content, club: Club, president: User | None, today: date) -> ClubCardOut:
    return ClubCardOut(
        id=content.id,
        title=content.title,
        summary=content.summary,
        club_type=club.club_type,
        campus_area=content.campus_area,
        logo_url=logo_of(club.logo_url),
        founded_year=club.founded_year,
        member_count=club.member_count,
        recruit_status=club.recruit_status,
        recruiting_now=is_recruiting(club, today),
        president_nickname=president.nickname if president is not None else None,
    )


def to_detail(db: Session, content: Content, viewer: User | None, today: date) -> ClubDetailOut:
    club = content.club
    status = my_status_of(db, club, viewer)
    card = to_card(content, club, club.president, today)
    return ClubDetailOut(
        **card.model_dump(),
        tags=list(content.tags or []),
        recruit_start=club.recruit_start,
        recruit_end=club.recruit_end,
        recruit_note=club.recruit_note,
        president=UserBrief(id=club.president.id, nickname=club.president.nickname, avatar_url=club.president.avatar_url)
        if club.president is not None
        else None,
        my_status=status,
        pending_count=pending_count_of(db, content.id) if status == "president" else None,
        created_at=content.created_at,
    )


def to_application(app: ClubApplication, user: User) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        club_id=app.club_id,
        user_id=user.id,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        reason=app.reason,
        status=app.status,
        created_at=app.created_at,
        reviewed_at=app.reviewed_at,
    )


@router.get("", response_model=ApiResponse[Page[ClubCardOut]], summary="社团列表")
def list_clubs(
    keyword: str | None = Query(default=None, max_length=50, description="关键词，空格分隔，需全部命中"),
    club_type: ClubType | None = Query(default=None, description="社团类型"),
    campus_area: CampusArea | None = Query(default=None, description="校区"),
    recruiting: bool | None = Query(default=None, description="true 只看今天在招新的，false 只看没在招新的"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ClubCardOut]]:
    today = shanghai_today()
    stmt = (
        select(Content, Club, User)
        .join(Club, Club.content_id == Content.id)
        .outerjoin(User, User.id == Club.president_id)
        .where(Content.type == "club", Content.status == "online")
    )
    if keyword:
        for word in keyword.split():
            if word:
                stmt = stmt.where(Content.search_text.ilike(f"%{escape_like(word)}%", escape="\\"))
    if club_type is not None:
        stmt = stmt.where(Club.club_type == club_type)
    if campus_area is not None:
        stmt = stmt.where(Content.campus_area == campus_area)
    if recruiting is True:
        stmt = stmt.where(recruiting_sql(today))
    elif recruiting is False:
        stmt = stmt.where(~recruiting_sql(today))
    # 正在招新的排在前面，方便首页信号旗和目录第一眼看到
    stmt = stmt.order_by(recruiting_sql(today).desc(), Club.member_count.desc(), Content.id.asc())

    rows, total = page_rows(db, stmt, page, page_size)
    cards = [to_card(content, club, president, today) for content, club, president in rows]
    return ok(Page(items=cards, total=total, page=page, page_size=page_size))


@router.get("/mine", response_model=ApiResponse[Page[MyClubOut]], summary="我加入的 / 我管理的社团")
def my_clubs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[MyClubOut]]:
    today = shanghai_today()
    stmt = (
        select(Content, Club, User, ClubMember.role)
        .join(Club, Club.content_id == Content.id)
        .join(ClubMember, and_(ClubMember.club_id == Content.id, ClubMember.user_id == user.id))
        .outerjoin(User, User.id == Club.president_id)
        .where(Content.type == "club", Content.status != "deleted")
        .order_by(ClubMember.role.desc(), Content.title.asc())
    )
    rows, total = page_rows(db, stmt, page, page_size)
    items: list[MyClubOut] = []
    for content, club, president, role in rows:
        card = to_card(content, club, president, today)
        items.append(
            MyClubOut(
                **card.model_dump(),
                my_role="president" if role == "president" or club.president_id == user.id else "member",
                pending_count=pending_count_of(db, content.id) if role == "president" or club.president_id == user.id else 0,
            )
        )
    return ok(Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/{club_id}", response_model=ApiResponse[ClubDetailOut], summary="社团详情")
def get_club(
    club_id: int,
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ClubDetailOut]:
    content = visible_club(db, club_id, viewer)
    # 会长自己看不计入浏览量，避免把后台刷新算进去
    if content.status == "online" and (viewer is None or viewer.id != content.club.president_id):
        db.execute(update(Content).where(Content.id == content.id).values(view_count=Content.view_count + 1))
        db.commit()
        content.view_count += 1
    return ok(to_detail(db, content, viewer, shanghai_today()))


@router.put("/{club_id}", response_model=ApiResponse[ClubDetailOut], summary="会长编辑简介和招新信息")
def update_club(
    club_id: int,
    body: ClubUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ClubDetailOut]:
    content, club = lock_club(db, club_id)
    require_president(club, user)
    today = shanghai_today()
    if body.recruit_status == "recruiting" and body.recruit_end is not None and body.recruit_end < today:
        raise BizError(40000, "参数错误：招新结束日期不能早于今天")

    content.summary = body.summary
    kept = [tag for tag in (content.tags or []) if tag not in STATUS_TAGS]
    type_label = ENUMS.club_type.get(club.club_type)
    if type_label and type_label not in kept:
        kept.insert(0, type_label)
    content.tags = kept + ["招新中" if body.recruit_status == "recruiting" else "社团"]
    club.recruit_status = body.recruit_status
    club.recruit_start = body.recruit_start
    club.recruit_end = body.recruit_end
    club.recruit_note = body.recruit_note or None
    content.search_text = build_search_text(content.title, content.summary, club.recruit_note, content.tags)
    db.commit()

    fresh = load_club(db, club_id)
    return ok(to_detail(db, fresh, user, today), "社团资料已保存")


@router.get("/{club_id}/members", response_model=ApiResponse[Page[MemberOut]], summary="成员列表")
def list_members(
    club_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[MemberOut]]:
    content = visible_club(db, club_id, viewer)
    stmt = (
        select(ClubMember, User)
        .join(User, User.id == ClubMember.user_id)
        .where(ClubMember.club_id == content.id)
        .order_by(ClubMember.role.desc(), ClubMember.joined_at.asc())
    )
    rows, total = page_rows(db, stmt, page, page_size)
    items = [
        MemberOut(
            user_id=member_user.id,
            nickname=member_user.nickname,
            avatar_url=member_user.avatar_url,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member, member_user in rows
    ]
    return ok(Page(items=items, total=total, page=page, page_size=page_size))


@router.post("/{club_id}/applications", response_model=ApiResponse[ApplicationOut], summary="申请入社")
def apply_club(
    club_id: int,
    body: ApplicationCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ApplicationOut]:
    content, club = lock_club(db, club_id)
    if content.status != "online":
        raise BizError(40431, "社团不存在")
    if user.id == club.president_id:
        raise BizError(40931, "你已经是该社团的会长")
    member = db.scalar(
        select(ClubMember).where(ClubMember.club_id == content.id, ClubMember.user_id == user.id)
    )
    if member is not None:
        raise BizError(40931, "你已经是该社团的成员")
    if not is_recruiting(club, shanghai_today()):
        raise BizError(42231, "该社团当前不在招新")
    pending = db.scalar(
        select(ClubApplication.id).where(
            ClubApplication.club_id == content.id,
            ClubApplication.user_id == user.id,
            ClubApplication.status == "pending",
        )
    )
    if pending is not None:
        raise BizError(40932, "你已提交过入社申请，请等待会长审核")

    app_row = ClubApplication(club_id=content.id, user_id=user.id, reason=body.reason, status="pending")
    db.add(app_row)
    if club.president_id is not None:
        notify(
            db,
            club.president_id,
            "club_apply",
            "收到新的入社申请",
            f"{user.nickname}申请加入{content.title}，请及时审核。",
            f"/clubs/{content.id}/applications",
        )
    try:
        # 先查再插入挡不住两人同时点。部分唯一索引 uq_club_app_pending 是最后一道门
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BizError(40932, "你已提交过入社申请，请等待会长审核")
    return ok(to_application(app_row, user), "申请已提交，请等待会长审核")


@router.get("/{club_id}/applications", response_model=ApiResponse[Page[ApplicationOut]], summary="会长查看入社申请")
def list_applications(
    club_id: int,
    status: ApplicationStatus | None = Query(default="pending", description="不传则只看待审核；可改为 approved / rejected"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ApplicationOut]]:
    content = load_club(db, club_id)
    if content is None or content.club is None or content.status == "deleted":
        raise BizError(40431, "社团不存在")
    require_president(content.club, user)
    stmt = (
        select(ClubApplication, User)
        .join(User, User.id == ClubApplication.user_id)
        .where(ClubApplication.club_id == content.id)
        .order_by(ClubApplication.created_at.asc(), ClubApplication.id.asc())
    )
    if status is not None:
        stmt = stmt.where(ClubApplication.status == status)
    rows, total = page_rows(db, stmt, page, page_size)
    return ok(
        Page(
            items=[to_application(app, applicant) for app, applicant in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/{club_id}/leave", response_model=ApiResponse[ClubDetailOut], summary="退出社团")
def leave_club(
    club_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ClubDetailOut]:
    content, club = lock_club(db, club_id)
    if user.id == club.president_id:
        raise BizError(42232, "会长不能退出社团")
    member = db.scalar(
        select(ClubMember)
        .where(ClubMember.club_id == content.id, ClubMember.user_id == user.id)
        .with_for_update()
    )
    if member is None:
        raise BizError(42233, "你还不是该社团的成员")
    if member.role == "president":
        raise BizError(42232, "会长不能退出社团")
    db.delete(member)
    # 和成员表同一事务：锁住社团行之后再减，不会和「通过申请」互相覆盖
    club.member_count = max(0, club.member_count - 1)
    if club.president_id is not None:
        notify(
            db,
            club.president_id,
            "club_left",
            "有成员退出社团",
            f"{user.nickname}退出了{content.title}。",
            f"/clubs/{content.id}",
        )
    db.commit()
    fresh = load_club(db, club_id)
    return ok(to_detail(db, fresh, user, shanghai_today()), "已退出社团")


def lock_application(db: Session, app_id: int) -> ClubApplication:
    app_row = db.scalar(select(ClubApplication).where(ClubApplication.id == app_id).with_for_update())
    if app_row is None:
        raise BizError(40432, "入社申请不存在")
    return app_row


def review(db: Session, app_id: int, user: User, approve: bool, note: str) -> ApiResponse[ApplicationOut]:
    """通过或拒绝。先锁申请行，再锁社团行，两个会长同时点只有一个能改状态。"""
    app_row = lock_application(db, app_id)
    content, club = lock_club(db, app_row.club_id)
    require_president(club, user)
    if app_row.status != "pending":
        raise BizError(40933, "这条申请已经处理过了")

    now = datetime.now(timezone.utc)
    applicant = db.get(User, app_row.user_id)
    if applicant is None:
        raise BizError(40432, "入社申请不存在")

    if approve:
        exists = db.scalar(
            select(ClubMember.user_id).where(ClubMember.club_id == content.id, ClubMember.user_id == applicant.id)
        )
        if exists is None:
            db.add(ClubMember(club_id=content.id, user_id=applicant.id, role="member", joined_at=now))
            club.member_count += 1
        app_row.status = "approved"
        app_row.reviewed_at = now
        notify(
            db,
            applicant.id,
            "club_approved",
            "入社申请已通过",
            f"你已加入{content.title}。",
            f"/clubs/{content.id}",
        )
        message = "已通过该申请"
    else:
        app_row.status = "rejected"
        app_row.reviewed_at = now
        body = note or f"{content.title}没有通过你的入社申请，可以修改理由后再次申请。"
        notify(db, applicant.id, "club_rejected", "入社申请未通过", body, f"/clubs/{content.id}")
        message = "已拒绝该申请"

    db.commit()
    return ok(to_application(app_row, applicant), message)


@application_router.get("/mine", response_model=ApiResponse[Page[MyApplicationOut]], summary="我提交的入社申请")
def my_applications(
    status: ApplicationStatus | None = Query(default=None, description="按状态筛选，不传返回全部"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[MyApplicationOut]]:
    stmt = (
        select(ClubApplication, Content.title)
        .join(Content, Content.id == ClubApplication.club_id)
        .where(ClubApplication.user_id == user.id)
        .order_by(ClubApplication.created_at.desc(), ClubApplication.id.desc())
    )
    if status is not None:
        stmt = stmt.where(ClubApplication.status == status)
    rows, total = page_rows(db, stmt, page, page_size)
    items = [
        MyApplicationOut(
            id=app.id,
            club_id=app.club_id,
            club_title=title,
            reason=app.reason,
            status=app.status,
            created_at=app.created_at,
            reviewed_at=app.reviewed_at,
        )
        for app, title in rows
    ]
    return ok(Page(items=items, total=total, page=page, page_size=page_size))


@application_router.post("/{app_id}/approve", response_model=ApiResponse[ApplicationOut], summary="会长通过入社申请")
def approve_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ApplicationOut]:
    return review(db, app_id, user, approve=True, note="")


@application_router.post("/{app_id}/reject", response_model=ApiResponse[ApplicationOut], summary="会长拒绝入社申请")
def reject_application(
    app_id: int,
    body: ApplicationRejectIn | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ApplicationOut]:
    note = body.note if body is not None else ""
    return review(db, app_id, user, approve=False, note=note)
