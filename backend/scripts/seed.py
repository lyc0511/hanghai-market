"""种子数据脚本（幂等）：清空全部业务表后重新造一套演示数据。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\seed.py

说明：
- 所有用户密码统一为 Test1234，哈希在运行时用 bcrypt 生成；
- 所有时间相对“现在”计算，任何时候运行数据都是新鲜的；
- 计数字段（member_count / enrolled_count）与明细表严格一致。
"""
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# 让 `python scripts/seed.py` 能找到 app 包（脚本目录不是 backend/）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select, text  # noqa: E402

from app.core.constants import CAMPUS_AREAS  # noqa: E402
from app.core.crypto import encrypt_text  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Activity,
    ActivitySignup,
    AiMessage,
    AuditLog,
    Category,
    Club,
    ClubApplication,
    ClubMember,
    Content,
    Item,
    Notification,
    Report,
    TradeIntent,
    User,
)

# 本地默认 Test1234；服务器上通过环境变量 SEED_PASSWORD 换成不公开的密码
PASSWORD = os.environ.get("SEED_PASSWORD") or "Test1234"
ALL_TABLES = [
    "audit_logs", "ai_messages", "reports", "notifications", "activity_signups",
    "club_applications", "club_members", "trade_intents", "activities", "clubs",
    "items", "contents", "categories", "users",
]

rnd = random.Random(2027)  # 固定随机种子：每次运行结构一致，便于写论文截图
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()


def ago(days: float = 0, hours: float = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours)


def at_evening(day_offset: int) -> datetime:
    """day_offset 天后的北京时间 19:00（即 UTC 11:00）。"""
    d = TODAY + timedelta(days=day_offset)
    return datetime(d.year, d.month, d.day, 11, 0, tzinfo=timezone.utc)


def build_search_text(title: str, summary: str, tags: list[str]) -> str:
    return " ".join([title, summary, *tags])


# ---------------------------------------------------------------- 用户
def seed_users(db) -> dict[str, User]:
    specs = [
        ("20230001", "管理员", "admin"),
        ("20230002", "卖家小王", "student"),
        ("20230003", "买家小李", "student"),
        ("20230004", "摄影协会会长", "student"),
        ("20230005", "新生小张", "student"),
        ("20230006", "卖家阿强", "student"),
    ] + [(f"202301{i:02d}", f"社团会长{i:02d}", "student") for i in range(1, 15)]

    users: dict[str, User] = {}
    for idx, (no, nickname, role) in enumerate(specs):
        u = User(
            student_no=no,
            nickname=nickname,
            password_hash=hash_password(PASSWORD),
            avatar_url=None,
            campus_area=CAMPUS_AREAS[idx % len(CAMPUS_AREAS)],
            wechat_id_enc=encrypt_text(f"wx_{no}"),  # 演示微信号，AES-GCM 加密存储
            wechat_visible=True,
            role=role,
            auth_source="open",
            status="active",
            created_at=ago(days=60 - idx),
            updated_at=ago(days=60 - idx),
        )
        db.add(u)
        users[no] = u
    db.flush()
    return users


# ---------------------------------------------------------------- 类目
ITEM_CATEGORIES = [
    ("教材书籍", "books"), ("电子数码", "digital"), ("生活用品", "life"),
    ("运动器材", "sports"), ("衣物配饰", "clothes"), ("其他", "other"),
]
CLUB_CATEGORIES = [
    ("学术科技", "academic"), ("文艺兴趣", "art"), ("体育运动", "sports"),
    ("公益实践", "public"), ("其他", "other"),
]
CLUB_CATEGORIES_MAP = {slug: name for name, slug in CLUB_CATEGORIES}


def seed_categories(db) -> tuple[dict[str, Category], dict[str, Category]]:
    item_cats, club_cats = {}, {}
    for i, (name, slug) in enumerate(ITEM_CATEGORIES, start=1):
        c = Category(type="item", name=name, slug=slug, sort_order=i)
        db.add(c)
        item_cats[slug] = c
    for i, (name, slug) in enumerate(CLUB_CATEGORIES, start=1):
        c = Category(type="club", name=name, slug=slug, sort_order=i)
        db.add(c)
        club_cats[slug] = c
    db.flush()
    return item_cats, club_cats


# ---------------------------------------------------------------- 物品
# (标题, 现价, 原价, 标签)；现价 0 表示免费赠送，共 8 条
ITEM_DATA: dict[str, list[tuple[str, int, int | None, list[str]]]] = {
    "books": [
        ("高等数学 同济第七版 上册", 15, 49, ["教材", "数学", "大一"]),
        ("高等数学 同济第七版 下册", 15, 46, ["教材", "数学", "大一"]),
        ("数据结构 C语言版（严蔚敏）", 20, 35, ["教材", "计算机", "考研"]),
        ("大学英语四级真题 2025 版", 0, 39, ["英语", "四级", "免费"]),
        ("线性代数 同济第六版", 10, 28, ["教材", "数学"]),
        ("概率论与数理统计 浙大第五版", 12, 42, ["教材", "数学", "考研"]),
        ("计算机网络 谢希仁第八版", 25, 59, ["教材", "计算机", "考研"]),
        ("考研政治 肖秀荣精讲精练", 18, 68, ["考研", "政治"]),
        ("C Primer Plus 第六版", 40, 89, ["编程", "C语言"]),
        ("大学物理学 第三版", 0, 45, ["教材", "物理", "免费"]),
    ],
    "digital": [
        ("小米充电宝 20000mAh", 45, 129, ["充电宝", "小米"]),
        ("罗技鼠标 M185", 30, 79, ["鼠标", "罗技", "无线"]),
        ("AirPods 第二代", 280, 999, ["耳机", "苹果", "蓝牙"]),
        ("小米手环 8", 90, 239, ["手环", "小米", "运动"]),
        ("iPad 第九代 64G", 500, 2499, ["平板", "苹果", "网课"]),
        ("机械键盘 Cherry 青轴", 160, 399, ["键盘", "机械键盘"]),
        ("漫步者蓝牙音箱 M230", 60, 159, ["音箱", "蓝牙"]),
        ("闪迪 U盘 128G", 0, 69, ["U盘", "存储", "免费"]),
        ("卡西欧 fx-991CN 计算器", 80, 169, ["计算器", "考试"]),
        ("索尼 WH-1000XM4 耳机", 450, 1899, ["耳机", "降噪", "索尼"]),
    ],
    "life": [
        ("宿舍小台灯 LED 护眼", 20, 69, ["台灯", "宿舍"]),
        ("美的电热水壶 1.5L", 25, 79, ["热水壶", "宿舍"]),
        ("折叠衣架 10 个装", 0, 19, ["衣架", "免费"]),
        ("小米床头灯", 50, 149, ["灯", "小米"]),
        ("宿舍床上书桌", 15, 39, ["书桌", "宿舍"]),
        ("收纳箱 三件套", 20, 59, ["收纳", "宿舍"]),
        ("晾衣架 不锈钢", 0, 35, ["晾衣", "免费"]),
        ("迷你加湿器", 18, 49, ["加湿器", "宿舍"]),
        ("自动折叠雨伞", 12, 39, ["雨伞"]),
        ("膳魔师保温杯 500ml", 70, 199, ["保温杯"]),
    ],
    "sports": [
        ("斯伯丁篮球 7 号", 60, 169, ["篮球", "斯伯丁"]),
        ("尤尼克斯羽毛球拍", 150, 459, ["羽毛球", "球拍"]),
        ("瑜伽垫 加厚 10mm", 0, 59, ["瑜伽", "健身", "免费"]),
        ("迪卡侬跳绳", 8, 29, ["跳绳", "体测"]),
        ("可调节哑铃 10kg", 80, 199, ["哑铃", "健身"]),
        ("红双喜乒乓球拍", 45, 128, ["乒乓球", "球拍"]),
        ("足球 5 号", 35, 99, ["足球"]),
        ("捷安特 ATX 山地车", 480, 1798, ["自行车", "代步"]),
        ("运动护膝 一对", 15, 49, ["护具", "运动"]),
        ("双翘滑板", 120, 299, ["滑板"]),
    ],
    "clothes": [
        ("优衣库羽绒服 M 码", 150, 499, ["羽绒服", "冬装"]),
        ("学士服 毕业照用", 40, 120, ["学士服", "毕业"]),
        ("匡威帆布鞋 41 码", 90, 429, ["鞋", "匡威"]),
        ("小米极简双肩包", 50, 149, ["背包", "小米"]),
        ("羊毛围巾", 0, 89, ["围巾", "冬装", "免费"]),
        ("面试西装 175/92A", 160, 599, ["西装", "面试", "求职"]),
        ("李宁运动外套", 70, 299, ["外套", "运动"]),
        ("针织毛线帽", 10, 39, ["帽子", "冬装"]),
        ("偏光太阳镜", 45, 159, ["眼镜", "配饰"]),
        ("卡西欧小方块手表", 100, 299, ["手表", "卡西欧"]),
    ],
    "other": [
        ("雅马哈 F310 民谣吉他", 350, 899, ["吉他", "乐器"]),
        ("四六级听力耳机", 20, 59, ["耳机", "四级", "六级"]),
        ("考研资料打包（数一英一）", 0, None, ["考研", "资料", "免费"]),
        ("绿萝盆栽", 5, 25, ["绿植", "宿舍"]),
        ("尤克里里 23 寸", 120, 299, ["尤克里里", "乐器"]),
        ("狼人杀桌游", 25, 68, ["桌游", "聚会"]),
        ("电动车头盔", 30, 89, ["头盔", "电动车"]),
        ("4K 画板（含画架）", 55, 160, ["美术", "画板"]),
        ("1000 片风景拼图", 20, 59, ["拼图", "休闲"]),
        ("GAN356 三阶魔方", 60, 159, ["魔方", "益智"]),
    ],
}
CONDITIONS = ["new", "like_new", "good", "fair"]


def seed_items(db, users, item_cats) -> list[Content]:
    # 主要卖家是小王、阿强，穿插其他同学，让列表看起来更真实
    owner_cycle = (
        ["20230002", "20230006"] * 2
        + ["20230002", "20230006", "20230101", "20230102", "20230005", "20230103"]
    )
    contents: list[Content] = []
    n = 0
    for slug, rows in ITEM_DATA.items():
        for title, price, original, tags in rows:
            owner = users[owner_cycle[n % len(owner_cycle)]]
            area = CAMPUS_AREAS[n % len(CAMPUS_AREAS)]
            condition = CONDITIONS[n % 4]
            summary = (
                f"{title}，{'免费送给有需要的同学' if price == 0 else f'诚心转让 {price} 元'}，"
                f"{area}可面交。"
            )
            created = ago(days=rnd.uniform(0.5, 30))
            c = Content(
                type="item",
                owner=owner,
                title=title,
                summary=summary,
                category_id=item_cats[slug].id,
                tags=tags,
                campus_area=area,
                status="online",
                view_count=rnd.randint(0, 300),
                search_text=build_search_text(title, summary, tags),
                embedding_text=None,  # AI 检索任务中再生成向量
                created_at=created,
                updated_at=created,
                item=Item(
                    price=Decimal(price),
                    original_price=Decimal(original) if original is not None else None,
                    condition=condition,
                    images=[f"/uploads/demo/item{n + 1}.jpg"],
                ),
            )
            db.add(c)
            contents.append(c)
            n += 1
    db.flush()
    return contents


# ---------------------------------------------------------------- 社团
# (名称, 类型, 成立年份, 简介, 是否招新, 招新文案)
CLUB_DATA = [
    ("ACM 集训队", "academic", 2008, "算法竞赛训练，备战 ICPC / CCPC。", True, "零基础也欢迎，每周两次集训，带你从入门到区域赛！"),
    ("机器人协会", "academic", 2012, "机器人设计与嵌入式开发，参加 RoboMaster 等赛事。", False, "本学期招新已结束，下学期见。"),
    ("数学建模协会", "academic", 2010, "数学建模培训与美赛、国赛组队。", False, "国赛备赛中，暂停招新。"),
    ("英语角", "academic", 2005, "每周英语口语交流与外教沙龙。", False, "欢迎随时来英语角旁听。"),
    ("天文爱好者协会", "academic", 2014, "天文观测、星空摄影与科普讲座。", False, "流星雨观测活动开放报名，招新暂停。"),
    ("摄影协会", "art", 2006, "人像、风光、纪实摄影交流，定期外拍与影展。", True, "有没有相机都没关系，一部手机也能拍出好照片！"),
    ("吉他社", "art", 2009, "民谣、指弹、弹唱教学与草坪音乐会。", True, "零基础教学，社里有公用吉他，来了就能弹。"),
    ("汉服社", "art", 2015, "传统服饰文化体验、汉服游园与礼仪学习。", True, "同袍们集合！社里提供汉服借穿。"),
    ("动漫社", "art", 2011, "动漫鉴赏、Cosplay 与同人创作。", True, "二次元的朋友们，这里就是你的家！"),
    ("话剧社", "art", 2007, "原创话剧排演与每学期公演。", False, "公演排练中，暂停招新。"),
    ("篮球社", "sports", 2004, "篮球训练、院系联赛与新生杯。", True, "新生杯组队中，喜欢篮球就来！"),
    ("羽毛球协会", "sports", 2008, "羽毛球技术教学与周末约球。", False, "场地有限，本学期名额已满。"),
    ("跑步俱乐部", "sports", 2016, "晨跑夜跑打卡，组队参加城市马拉松。", False, "欢迎随时加入夜跑，正式招新下学期开放。"),
    ("轮滑社", "sports", 2013, "平花、速滑教学，周末刷街。", False, "装备不足，暂停招新。"),
    ("青年志愿者协会", "public", 2003, "社区服务、大型赛会志愿与支农活动。", True, "用行动温暖他人，志愿时长可认定。"),
    ("支教协会", "public", 2012, "周末线上支教与暑期乡村支教。", False, "暑期支教队已组建完成。"),
    ("环保协会", "public", 2010, "垃圾分类宣传、旧物回收与校园环保行动。", False, "欢迎参加环保活动，招新下学期开放。"),
    ("辩论队", "other", 2005, "华语辩论训练，参加校内外辩论赛。", True, "敢想敢说，思辨无界，等你来辩！"),
    ("桌游社", "other", 2017, "狼人杀、剧本杀、德式桌游周末局。", False, "社团满员，欢迎周末来玩。"),
    ("创业协会", "other", 2014, "创业沙龙、项目路演与创新创业大赛辅导。", False, "项目路演季，暂停招新。"),
]


def seed_clubs(db, users, club_cats) -> dict[str, Content]:
    # 摄影协会 → 20230004；其余 19 个依次分给社团会长01–14，会长01–05 再各兼任一个
    presidents = iter([f"202301{i:02d}" for i in range(1, 15)] + [f"202301{i:02d}" for i in range(1, 6)])
    clubs: dict[str, Content] = {}
    for idx, (name, ctype, year, summary, recruiting, note) in enumerate(CLUB_DATA):
        pres_no = "20230004" if name == "摄影协会" else next(presidents)
        president = users[pres_no]
        if recruiting:
            r_start, r_end = TODAY - timedelta(days=15), TODAY + timedelta(days=15)
        else:
            r_start, r_end = TODAY - timedelta(days=200), TODAY - timedelta(days=170)
        tags = [CLUB_CATEGORIES_MAP[ctype], "招新中" if recruiting else "社团"]
        created = ago(days=rnd.uniform(40, 90))
        c = Content(
            type="club",
            owner=president,
            title=name,
            summary=summary,
            category_id=club_cats[ctype].id,
            tags=tags,
            campus_area=CAMPUS_AREAS[idx % len(CAMPUS_AREAS)],
            status="online",
            view_count=rnd.randint(50, 800),
            search_text=build_search_text(name, summary + " " + note, tags),
            created_at=created,
            updated_at=created,
            club=Club(
                logo_url=f"/uploads/demo/club{idx + 1}.png",
                club_type=ctype,
                founded_year=year,
                president_id=president.id,
                member_count=0,  # 插完成员后回填
                recruit_status="recruiting" if recruiting else "closed",
                recruit_start=r_start,
                recruit_end=r_end,
                recruit_note=note,
            ),
        )
        db.add(c)
        clubs[name] = c
    db.flush()
    return clubs



def seed_club_members(db, users, clubs) -> None:
    students = [u for u in users.values() if u.role == "student"]
    for name, c in clubs.items():
        club = c.club
        db.add(ClubMember(club_id=c.id, user_id=club.president_id, role="president", joined_at=c.created_at))
        exclude = {club.president_id, users["20230003"].id}  # 小李留给“申请入社”演示
        if name == "吉他社":
            exclude.add(users["20230005"].id)  # 小张通过入社申请加入，单独插入
        pool = [u for u in students if u.id not in exclude]
        for u in rnd.sample(pool, rnd.randint(4, 8)):
            db.add(ClubMember(club_id=c.id, user_id=u.id, role="member", joined_at=ago(days=rnd.uniform(5, 35))))
    db.flush()


def seed_club_applications(db, users, clubs) -> dict[str, ClubApplication]:
    approved = ClubApplication(
        club_id=clubs["吉他社"].id,
        user_id=users["20230005"].id,
        reason="从小喜欢音乐，想学会弹唱，希望加入吉他社！",
        status="approved",
        reviewed_at=ago(days=2),
        created_at=ago(days=4),
    )
    pending = ClubApplication(
        club_id=clubs["摄影协会"].id,
        user_id=users["20230003"].id,
        reason="平时喜欢用手机拍校园风景，想系统学习摄影技巧。",
        status="pending",
        created_at=ago(hours=6),
    )
    db.add_all([approved, pending])
    # 审批通过 → 成为成员
    db.add(ClubMember(club_id=clubs["吉他社"].id, user_id=users["20230005"].id, role="member", joined_at=ago(days=2)))
    db.flush()
    return {"approved": approved, "pending": pending}


def refresh_member_counts(db, clubs) -> None:
    for c in clubs.values():
        c.club.member_count = db.scalar(
            select(func.count()).select_from(ClubMember).where(ClubMember.club_id == c.id)
        )
    db.flush()


# ---------------------------------------------------------------- 活动
# (社团, 标题, 开始距今天数, 时长小时, 地点, 容量, 报名人数, 标签)
ACTIVITY_DATA = [
    ("吉他社", "草坪音乐会·秋日专场", 2, 2, "图书馆前草坪", 15, 15, ["音乐", "晚会"]),            # 下周·满员
    ("摄影协会", "秋日校园扫街外拍", 4, 3, "南门集合", 30, 3, ["摄影", "外拍"]),
    ("篮球社", "新生杯篮球赛 小组赛", 6, 3, "东区篮球场", 60, 2, ["篮球", "比赛"]),
    ("ACM 集训队", "算法入门讲座：从暴力到动态规划", 9, 2, "教学楼 A301", 100, 2, ["算法", "讲座"]),
    ("汉服社", "汉服游园会", 14, 4, "荷花池", 50, 0, ["汉服", "游园"]),                       # 空活动
    ("动漫社", "动漫电影放映夜", 20, 3, "学生活动中心 202", 80, 1, ["动漫", "放映"]),
    ("辩论队", "新生辩论赛 初赛", 27, 3, "文科楼报告厅", 40, 1, ["辩论", "比赛"]),
    ("青年志愿者协会", "社区敬老院探访", -3, 4, "东校门集合", 20, 4, ["志愿", "公益"]),       # 已结束
    ("天文爱好者协会", "猎户座流星雨观测", -10, 4, "体育场看台", 30, 3, ["天文", "观测"]),     # 已结束
    ("环保协会", "旧物回收市集", -20, 5, "第二食堂门口", 100, 2, ["环保", "市集"]),            # 已结束
]


def seed_activities(db, users, clubs) -> list[Content]:
    students = [u for u in users.values() if u.role == "student"]
    result = []
    for club_name, title, offset, hours, location, capacity, enrolled, tags in ACTIVITY_DATA:
        club_content = clubs[club_name]
        start = at_evening(offset)
        end = start + timedelta(hours=hours)
        deadline = start - timedelta(days=1)
        summary = f"{club_name}主办：{title}，地点 {location}，限 {capacity} 人，欢迎全校同学参加。"
        created = min(start - timedelta(days=7), ago(days=1))
        c = Content(
            type="activity",
            owner_id=club_content.owner_id,
            title=title,
            summary=summary,
            category_id=None,
            tags=tags,
            campus_area=club_content.campus_area,
            status="online",
            view_count=rnd.randint(20, 500),
            search_text=build_search_text(title, summary, tags),
            created_at=created,
            updated_at=created,
            activity=Activity(
                club_id=club_content.id,
                start_time=start,
                end_time=end,
                location=location,
                capacity=capacity,
                enrolled_count=enrolled,
                signup_deadline=deadline,
            ),
        )
        db.add(c)
        db.flush()
        # 报名记录与 enrolled_count 严格一致；演示账号小李、小张优先报名
        pool = [users["20230003"], users["20230005"]] + rnd.sample(
            [u for u in students if u.student_no not in ("20230003", "20230005")], len(students) - 2
        )
        for i, u in enumerate(pool[:enrolled]):
            db.add(ActivitySignup(
                activity_id=c.id,
                user_id=u.id,
                status="signed",
                created_at=min(created + timedelta(hours=1 + i), deadline - timedelta(hours=1)),
            ))
        result.append(c)
    db.flush()
    return result


# ---------------------------------------------------------------- 交易意向
def seed_intents(db, users, items) -> tuple[list[TradeIntent], Content]:
    by_owner: dict[str, list[Content]] = {"20230002": [], "20230006": []}
    for c in items:
        if c.owner.student_no in by_owner:
            by_owner[c.owner.student_no].append(c)
    wang, qiang = by_owner["20230002"], by_owner["20230006"]

    # (物品, 买家学号, 状态, 留言, 多少天前)
    plan = [
        (wang[0], "20230003", "pending", "同学你好，这本书还在吗？想今晚面交。", 0.2),
        (qiang[1], "20230005", "pending", "请问可以便宜一点吗？", 0.5),
        (wang[2], "20230003", "accepted", "想要，周末在图书馆门口面交可以吗？", 2),
        (qiang[3], "20230101", "accepted", "成色怎么样？可以先看看实物吗？", 3),
        (wang[4], "20230005", "rejected", "能不能再降 10 块？", 4),
        (qiang[5], "20230003", "completed", "已经在宿舍楼下交易，谢谢！", 8),
        (wang[6], "20230102", "completed", "东西很好，已付款。", 10),
        (qiang[7], "20230003", "cancelled", "不好意思，已经买到了，取消一下。", 6),
    ]
    intents = []
    for item_c, buyer_no, status, msg, days in plan:
        created = ago(days=days)
        updated = created + timedelta(hours=3) if status != "pending" else created
        intent = TradeIntent(
            item_id=item_c.id,
            buyer_id=users[buyer_no].id,
            seller_id=item_c.owner_id,
            message=msg,
            status=status,
            contact_revealed_at=updated if status in ("accepted", "completed") else None,
            created_at=created,
            updated_at=updated,
        )
        db.add(intent)
        intents.append(intent)
        if status == "completed":
            # 成交：物品标记售出并下架
            item_c.item.sold_at = updated + timedelta(days=1)
            item_c.status = "offline"
            item_c.updated_at = item_c.item.sold_at

    # 再挑一件阿强的、未被意向涉及的物品演示“审核驳回”
    used = {p[0].id for p in plan}
    rejected = next(c for c in qiang if c.id not in used)
    rejected.status = "rejected"
    rejected.reject_reason = "图片与描述不符，请补充实物照片后重新提交。"
    rejected.updated_at = ago(days=1)
    db.flush()
    return intents, rejected


# ---------------------------------------------------------------- 通知 / 举报
def seed_notifications(db, users, intents, rejected_item, clubs) -> None:
    i = intents
    rows = [
        (i[0].seller_id, "intent_new", "收到新的购买意向", f"买家小李对你的物品发起了购买意向：{i[0].message}", f"/items/{i[0].item_id}", False, 0.2),
        (i[1].seller_id, "intent_new", "收到新的购买意向", f"新生小张对你的物品发起了购买意向：{i[1].message}", f"/items/{i[1].item_id}", False, 0.5),
        (i[2].seller_id, "intent_new", "收到新的购买意向", "买家小李对你的物品发起了购买意向。", f"/items/{i[2].item_id}", True, 2),
        (i[2].buyer_id, "intent_accepted", "卖家已接受你的意向", "卖家已同意交易，可在“我的意向”中查看对方微信号。", "/me/intents", False, 1.9),
        (i[3].buyer_id, "intent_accepted", "卖家已接受你的意向", "卖家已同意交易，可在“我的意向”中查看对方微信号。", "/me/intents", True, 2.9),
        (users["20230005"].id, "club_approved", "入社申请已通过", "恭喜你加入吉他社！", f"/clubs/{clubs['吉他社'].id}", False, 2),
        (rejected_item.owner_id, "content_rejected", "物品审核未通过", f"你发布的「{rejected_item.title}」未通过审核：{rejected_item.reject_reason}", f"/items/{rejected_item.id}", False, 1),
        (users["20230004"].id, "club_apply", "收到新的入社申请", "买家小李申请加入摄影协会，请及时审核。", f"/clubs/{clubs['摄影协会'].id}", False, 0.25),
    ]
    for user_id, ntype, title, body, link, is_read, days in rows:
        db.add(Notification(
            user_id=user_id, type=ntype, title=title, body=body, link=link,
            is_read=is_read, created_at=ago(days=days),
        ))
    db.flush()


def seed_reports(db, users, items, activities) -> None:
    db.add_all([
        Report(
            target_type="item",
            target_id=items[13].id,
            reporter_id=users["20230003"].id,
            reason="fraud",
            description="价格明显低于市场价，卖家要求先转账再发货，疑似诈骗。",
            status="pending",
            created_at=ago(hours=10),
        ),
        Report(
            target_type="activity",
            target_id=activities[5].id,
            reporter_id=users["20230005"].id,
            reason="false_info",
            description="活动地点写错了，学生活动中心 202 本周在装修。",
            status="pending",
            created_at=ago(hours=30),
        ),
    ])
    db.flush()


# ---------------------------------------------------------------- 主流程
def main() -> None:
    db = SessionLocal()
    try:
        db.execute(text(f"TRUNCATE {', '.join(ALL_TABLES)} RESTART IDENTITY CASCADE"))

        users = seed_users(db)
        item_cats, club_cats = seed_categories(db)
        items = seed_items(db, users, item_cats)
        clubs = seed_clubs(db, users, club_cats)
        seed_club_members(db, users, clubs)
        seed_club_applications(db, users, clubs)
        refresh_member_counts(db, clubs)
        activities = seed_activities(db, users, clubs)
        intents, rejected_item = seed_intents(db, users, items)
        seed_notifications(db, users, intents, rejected_item, clubs)
        seed_reports(db, users, items, activities)
        db.commit()

        def count(model) -> int:
            return db.scalar(select(func.count()).select_from(model))

        print("种子数据写入完成：")
        print(f"  用户         {count(User)}")
        print(f"  类目         {count(Category)}")
        print(f"  物品         {count(Item)}")
        print(f"  社团         {count(Club)}")
        print(f"  活动         {count(Activity)}")
        print(f"  交易意向     {count(TradeIntent)}")
        print(f"  社团成员     {count(ClubMember)}")
        print(f"  入社申请     {count(ClubApplication)}")
        print(f"  活动报名     {count(ActivitySignup)}")
        print(f"  通知         {count(Notification)}")
        print(f"  举报         {count(Report)}")
        print(f"  AI 对话      {count(AiMessage)}")
        print(f"  管理日志     {count(AuditLog)}")
        print(f"  内容总数     {count(Content)}（物品 + 社团 + 活动）")
        print("所有账号密码均为 Test1234" if PASSWORD == "Test1234" else "所有账号密码为环境变量 SEED_PASSWORD 的值")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
