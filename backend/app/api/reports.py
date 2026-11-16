"""举报：同学举报违规的物品 / 社团 / 活动 / 帖子 / 评论，管理员核实后处理。

状态流转：
    pending ──管理员「举报属实」──▶ resolved（可同时下架被举报内容）
       └────管理员「驳回举报」──▶ dismissed
处理结果写进 handle_note 并通知举报人；下架时同时通知内容发布者。
选择「属实并下架」时，同一内容其余待处理的举报一并标为属实，免得管理员重复处理。

规则：
    - 只能举报正在展示（online）的内容，不能举报自己发布的；
    - 同一人对同一内容只能有一条待处理的举报；
    - 理由选「其他」时必须写补充说明。

业务错误码：
    40451 被举报的内容不存在      42251 不能举报自己发布的内容
    40951 已举报过，等待处理中    42252 选择「其他」时请填写说明
    40452 举报不存在             40952 该举报已处理过
"""
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.notifications import notify
from app.core.exceptions import BizError
from app.db.session import get_db
from app.api.post_comments import take_comment_down
from app.models import AuditLog, Content, PostComment, Report, User
from app.schemas.common import ApiResponse, Page, ok
from app.schemas.report import (
    AdminReportOut,
    ReportCreateIn,
    ReportHandleIn,
    ReportOut,
    ReportStatus,
    ReportTarget,
    TargetType,
    UserMini,
)

router = APIRouter(prefix="/reports", tags=["举报"])
admin_router = APIRouter(prefix="/admin/reports", tags=["管理后台"])

TYPE_LABELS = {"item": "物品", "club": "社团", "activity": "活动", "post": "帖子", "comment": "评论"}
TYPE_PATHS = {"item": "items", "club": "clubs", "activity": "activities", "post": "wall"}
REASON_LABELS = {
    "fraud": "疑似诈骗", "prohibited": "违禁物品", "false_info": "虚假信息",
    "spam": "广告刷屏", "abuse": "辱骂骚扰", "privacy": "泄露隐私", "other": "其他",
}


@dataclass
class Target:
    """被举报的对象。物品 / 社团 / 活动 / 帖子是 contents 里的一行，评论是 post_comments 里的一行，
    这里把两种统一成同样的几个字段，后面的代码就不用到处区分了。"""

    obj: Content | PostComment
    title: str
    status: str
    owner_id: int
    link: str


def load_target(db: Session, target_type: str, target_id: int, *, lock: bool = False) -> Target | None:
    if target_type == "comment":
        stmt = select(PostComment).where(PostComment.id == target_id)
        cm = db.scalar(stmt.with_for_update() if lock else stmt)
        if cm is None:
            return None
        return Target(cm, cm.body[:40], cm.status, cm.user_id, f"/wall/{cm.post_id}")
    stmt = select(Content).where(Content.id == target_id, Content.type == target_type)
    c = db.scalar(stmt.with_for_update() if lock else stmt)
    if c is None:
        return None
    return Target(c, c.title, c.status, c.owner_id, f"/{TYPE_PATHS[target_type]}/{c.id}")


def target_of(r: Report, t: Target | None) -> ReportTarget:
    return ReportTarget(
        type=r.target_type,
        id=r.target_id,
        title=t.title if t else "（内容已删除）",
        status=t.status if t else "deleted",
        link=t.link if t else "/wall" if r.target_type == "comment" else f"/{TYPE_PATHS[r.target_type]}/{r.target_id}",
    )


def to_out(r: Report, t: Target | None) -> ReportOut:
    return ReportOut(
        id=r.id, target=target_of(r, t), reason=r.reason, description=r.description,
        status=r.status, handle_note=r.handle_note, created_at=r.created_at,
    )


def mini(u: User | None) -> UserMini | None:
    return UserMini(id=u.id, nickname=u.nickname, student_no=u.student_no) if u else None


def to_admin_out(db: Session, r: Report) -> AdminReportOut:
    t = load_target(db, r.target_type, r.target_id)
    pending = db.scalar(
        select(func.count()).select_from(Report).where(
            Report.target_type == r.target_type, Report.target_id == r.target_id, Report.status == "pending"
        )
    )
    return AdminReportOut(
        **to_out(r, t).model_dump(),
        reporter=mini(db.get(User, r.reporter_id)),
        owner=mini(db.get(User, t.owner_id)) if t else UserMini(id=0, nickname="未知"),
        handler=mini(db.get(User, r.handled_by)) if r.handled_by else None,
        same_target_pending=int(pending or 0),
    )


# ---------------------------------------------------------------- 同学端

@router.post("", response_model=ApiResponse[ReportOut], summary="举报物品 / 社团 / 活动 / 帖子 / 评论")
def create_report(
    body: ReportCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ReportOut]:
    t = load_target(db, body.target_type, body.target_id)
    if t is None or t.status != "online":
        raise BizError(40451, f"被举报的{TYPE_LABELS[body.target_type]}不存在或已下架")
    if t.owner_id == user.id:
        raise BizError(42251, "不能举报自己发布的内容")
    desc = (body.description or "").strip() or None
    if body.reason == "other" and not desc:
        raise BizError(42252, "选择「其他」时请简单说明举报原因")

    dup = db.scalar(
        select(Report.id).where(
            Report.reporter_id == user.id,
            Report.target_type == body.target_type,
            Report.target_id == body.target_id,
            Report.status == "pending",
        )
    )
    if dup is not None:
        raise BizError(40951, "你已经举报过该内容，管理员正在处理")

    r = Report(target_type=body.target_type, target_id=body.target_id, reporter_id=user.id, reason=body.reason, description=desc)
    db.add(r)
    db.commit()
    db.refresh(r)
    return ok(to_out(r, t), "举报已提交，管理员会尽快核实")


@router.get("/mine", response_model=ApiResponse[Page[ReportOut]], summary="我的举报")
def list_my_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[ReportOut]]:
    where = Report.reporter_id == user.id
    total = db.scalar(select(func.count()).select_from(Report).where(where)) or 0
    rows = db.scalars(
        select(Report).where(where).order_by(Report.created_at.desc(), Report.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [to_out(r, load_target(db, r.target_type, r.target_id)) for r in rows]
    return ok(Page(items=items, total=total, page=page, page_size=page_size))


# ---------------------------------------------------------------- 管理端

@admin_router.get("", response_model=ApiResponse[Page[AdminReportOut]], summary="举报列表")
def list_reports(
    status: ReportStatus = Query(default="pending"),
    target_type: TargetType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[Page[AdminReportOut]]:
    where = [Report.status == status]
    if target_type:
        where.append(Report.target_type == target_type)
    total = db.scalar(select(func.count()).select_from(Report).where(*where)) or 0
    # 待处理先来先办；已处理的最新在前
    order = Report.created_at.asc() if status == "pending" else Report.created_at.desc()
    rows = db.scalars(
        select(Report).where(*where).order_by(order, Report.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return ok(Page(items=[to_admin_out(db, r) for r in rows], total=total, page=page, page_size=page_size))


@admin_router.post("/{report_id}/handle", response_model=ApiResponse[AdminReportOut], summary="处理举报（属实 / 驳回）")
def handle_report(
    report_id: int,
    body: ReportHandleIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[AdminReportOut]:
    # 行锁：两个管理员同时处理同一条时，后到的会看到「已处理过」
    r = db.scalar(select(Report).where(Report.id == report_id).with_for_update())
    if r is None:
        raise BizError(40452, "举报不存在")
    if r.status != "pending":
        raise BizError(40952, "该举报已处理过")

    note = body.note.strip()
    t = load_target(db, r.target_type, r.target_id, lock=True)
    title = t.title if t else "（已删除的内容）"
    label = TYPE_LABELS[r.target_type]
    took_down = False

    if body.action == "dismiss":
        r.status = "dismissed"
        notify(db, r.reporter_id, "report_dismissed", "举报未成立",
               f"你对{label}「{title}」的举报经核实未发现违规：{note}", "/me/reports")
    else:
        r.status = "resolved"
        notify(db, r.reporter_id, "report_resolved", "举报已处理",
               f"你对{label}「{title}」的举报已核实处理：{note}", "/me/reports")
        if body.takedown and t is not None and t.status == "online":
            if isinstance(t.obj, PostComment):
                take_comment_down(db, t.obj, by_admin=True)  # 同时把帖子的评论数减 1
            else:
                t.obj.status = "offline"
            took_down = True
            notify(db, t.owner_id, "content_takedown", f"你的{label}已被下架",
                   f"你发布的{label}「{title}」因「{REASON_LABELS[r.reason]}」被举报，经核实已下架：{note}", t.link)
    r.handled_by = admin.id
    r.handle_note = note

    # 已经下架了，同一内容其余待处理的举报一并办结
    others = []
    if took_down:
        others = db.scalars(
            select(Report).where(
                Report.target_type == r.target_type, Report.target_id == r.target_id,
                Report.status == "pending", Report.id != r.id,
            )
        ).all()
        for o in others:
            o.status, o.handled_by, o.handle_note = "resolved", admin.id, note
            notify(db, o.reporter_id, "report_resolved", "举报已处理",
                   f"你对{label}「{title}」的举报已核实，内容已下架：{note}", "/me/reports")

    db.add(AuditLog(
        admin_id=admin.id,
        action=f"{body.action}_report",
        target_type="report",
        target_id=r.id,
        detail={
            "content_type": r.target_type, "content_id": r.target_id, "note": note,
            "takedown": took_down, "also_resolved": [o.id for o in others],
        },
    ))
    db.commit()
    db.expire_all()

    if body.action == "dismiss":
        msg = "已驳回举报"
    elif took_down:
        msg = f"已处理，{label}已下架" + (f"，另有 {len(others)} 条同内容举报一并办结" if others else "")
    else:
        msg = "已标记为属实"
    return ok(to_admin_out(db, db.get(Report, report_id)), msg)
