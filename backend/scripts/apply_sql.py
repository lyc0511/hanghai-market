"""在本地数据库上执行一个 SQL 文件（用 .env 里的 DATABASE_URL 连接），主要用来跑 sql/ 下的升级脚本。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\apply_sql.py sql\\upgrade_T16_wall.sql

整个文件在一个事务里执行：中途出错会全部回滚，不会留下执行了一半的状态。
服务器上不用这个脚本，直接用 psql（见 docs/部署指南.md）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import engine  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("用法：python scripts/apply_sql.py <SQL 文件路径>")
    path = Path(sys.argv[1])
    if not path.is_file():
        sys.exit(f"找不到文件：{path}")

    sql = path.read_text(encoding="utf-8")
    # exec_driver_sql 把整段 SQL 原样交给数据库，不解析其中的冒号、百分号
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    print(f"已执行：{path}")


if __name__ == "__main__":
    main()
