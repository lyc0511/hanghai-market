"""演示数据「保鲜」脚本：把数据库里所有时间整体往后平移，让演示数据看起来像这周刚造的。

为什么需要它：种子数据的时间是按“运行 seed.py 那天”算的，过几周再演示时，
活动全都已经结束、招新也过期了。重新跑 seed.py 会清空所有数据（包括自己后来发的物品），
这个脚本只平移时间，不增删任何记录。

做法：
    - 找到最新一条内容（物品 / 社团 / 活动）的发布日期，作为「数据的今天」；
    - 计算它距离真正的今天（北京时间）差几周，按「整周」平移：
      星期几不变（周六的活动平移后还是周六），时长、先后顺序也都不变；
    - 平移范围：public schema 下所有 timestamptz / date 类型的列（自动发现，新增表也能覆盖）。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\refresh_demo_dates.py            # 只预览，不改数据
    .venv\\Scripts\\python scripts\\refresh_demo_dates.py --apply    # 真正执行（单个事务，出错全部回滚）
    .venv\\Scripts\\python scripts\\refresh_demo_dates.py --weeks 2 --apply   # 手动指定平移周数
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402

BJ = ZoneInfo("Asia/Shanghai")


def time_columns(db) -> list[tuple[str, str]]:
    rows = db.execute(text("""
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name AND t.table_type = 'BASE TABLE'
        WHERE c.table_schema = 'public' AND c.data_type IN ('timestamp with time zone', 'date')
        ORDER BY c.table_name, c.ordinal_position
    """)).all()
    return [(t, c) for t, c in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="把演示数据的时间整体平移到最近")
    parser.add_argument("--weeks", type=int, default=None, help="平移周数；不填则自动计算")
    parser.add_argument("--apply", action="store_true", help="真正写入数据库；不加只预览")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        latest = db.execute(text("SELECT max(created_at) FROM contents")).scalar()
        if latest is None:
            print("contents 表是空的，请先运行 scripts/seed.py")
            return
        data_day = latest.astimezone(BJ).date()
        today = datetime.now(BJ).date()
        weeks = args.weeks if args.weeks is not None else (today - data_day).days // 7
        print(f"数据中最新发布日期：{data_day}，今天（北京时间）：{today}")
        if weeks <= 0:
            print("数据已经是最近一周的，不需要平移。")
            return

        cols = time_columns(db)
        print(f"计划平移 {weeks} 周（{weeks * 7} 天），涉及 {len(cols)} 个时间列：")
        for t, c in cols:
            print(f"  - {t}.{c}")

        upcoming_before = db.execute(text("SELECT count(*) FROM activities WHERE start_time > now()")).scalar()
        shift = f"INTERVAL '{weeks * 7} days'"
        for t, c in cols:
            # 表名、列名来自 information_schema，不是用户输入；用双引号包起来防止关键字冲突
            db.execute(text(f'UPDATE "{t}" SET "{c}" = "{c}" + {shift} WHERE "{c}" IS NOT NULL'))
        upcoming_after = db.execute(text("SELECT count(*) FROM activities WHERE start_time > now()")).scalar()
        print(f"即将开始的活动：{upcoming_before} 个 → {upcoming_after} 个")

        if args.apply:
            db.commit()
            print("已写入数据库。")
        else:
            db.rollback()
            print("预览模式，已回滚，数据库没有任何变化。加 --apply 才会真正执行。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
