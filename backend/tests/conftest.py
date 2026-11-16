"""测试公共夹具。

隔离方式：每个测试开一个数据库连接并 BEGIN，接口里的 commit() 变成 SAVEPOINT，
测试结束整体 ROLLBACK —— 测试里造的用户、物品、举报……都不会留在数据库里，演示数据不受影响。

（并发测试需要多个连接真正提交，见 test_concurrency.py，它自己负责清理。）

运行：在 backend 目录下  .venv\\Scripts\\python -m pytest
"""
import itertools
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.crypto import encrypt_text  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.session import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category, User  # noqa: E402

# 测试用户学号段：2999xxxx，和演示账号（2023xxxx）分开
_student_no = itertools.count(29990001)


@pytest.fixture()
def db():
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()


@pytest.fixture(autouse=True)
def no_real_ai_prescreen(monkeypatch):
    """投稿后的 AI 预审是后台任务，会真的调用大模型。测试里默认关掉，避免花钱、变慢、结果不稳定；
    专门测预审的用例（test_wall_admin.py）直接调用 prescreen_post 并使用假的大模型回复。"""
    from app.api import post_ai

    monkeypatch.setattr(post_ai, "prescreen_in_background", lambda post_id: None)


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    """造一个用户，返回 (user, 请求头)。"""

    def _make(nickname: str = "测试同学", role: str = "student", wechat: str | None = "test_wx") -> tuple[User, dict]:
        u = User(
            student_no=str(next(_student_no)),
            nickname=nickname,
            password_hash="x",  # 测试直接签发令牌，不走密码登录
            role=role,
            campus_area="黄埔校区",
            wechat_id_enc=encrypt_text(wechat) if wechat else None,
        )
        db.add(u)
        db.flush()
        token, _ = create_access_token(u.id)
        return u, {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def item_category_id(db) -> int:
    return db.scalar(select(Category.id).where(Category.type == "item").limit(1))


def call(client: TestClient, method: str, url: str, headers: dict | None = None, **kw) -> dict:
    """发请求并返回统一响应体 {code, message, data}。"""
    r = client.request(method, "/api" + url, headers=headers, **kw)
    return r.json()
