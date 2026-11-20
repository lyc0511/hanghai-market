"""使用独立事务验证交易锁；只创建和清理本测试的数据。"""
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.crypto import encrypt_text
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models import Content, Item, Notification, TradeIntent, User


@pytest.fixture
def trade_data():
    with SessionLocal() as db:
        users = [User(student_no=str(uuid4().int)[:20], nickname="交易并发测试", password_hash="x",
                      wechat_id_enc=encrypt_text("test_wx")) for _ in range(3)]
        db.add_all(users)
        db.flush()
        ids = [u.id for u in users]
        content = Content(type="item", owner_id=ids[0], title="交易并发测试", status="online")
        db.add(content)
        db.flush()
        item_id = content.id
        db.add(Item(content_id=item_id, price=10))
        db.commit()
        try:
            yield item_id, ids
        finally:
            db.rollback()
            db.execute(delete(Notification).where(Notification.user_id.in_(ids)))
            db.execute(delete(TradeIntent).where(TradeIntent.item_id == item_id))
            db.execute(delete(Item).where(Item.content_id == item_id))
            db.execute(delete(Content).where(Content.id == item_id))
            db.execute(delete(User).where(User.id.in_(ids)))
            db.commit()


def request(user_id, path, **kwargs):
    token = create_access_token(user_id, "x")[0]  # 与 trade_data 的测试账号一致
    with TestClient(app) as client:
        response = client.post(path, headers={"Authorization": f"Bearer {token}"}, **kwargs)
        assert response.status_code == 200, response.text
        return response.json()["code"]


def test_create_intent_waits_for_offline(trade_data):
    item_id, ids = trade_data
    with SessionLocal() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        content = holder.scalar(select(Content).where(Content.id == item_id).with_for_update())
        started = threading.Event()

        def create():
            started.set()
            return request(ids[1], "/api/intents", json={"item_id": item_id})

        future = pool.submit(create)
        try:
            assert started.wait(5)
            # 请求必须等待物品锁，而不是使用下架前的快照继续创建。
            from concurrent.futures import wait
            assert not wait([future], timeout=1.5).done
            content.status = "offline"
            holder.commit()
            assert future.result(timeout=10) == 42204
            with SessionLocal() as check:
                assert check.scalar(select(TradeIntent.id).where(TradeIntent.item_id == item_id)) is None
        finally:
            holder.rollback()


def test_complete_locks_item_before_intent(trade_data):
    item_id, ids = trade_data
    with SessionLocal() as setup:
        intent = TradeIntent(item_id=item_id, buyer_id=ids[1], seller_id=ids[0], status="accepted")
        setup.add(intent)
        setup.commit()
        intent_id = intent.id
    with SessionLocal() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.scalar(select(Content).where(Content.id == item_id).with_for_update())
        future = pool.submit(request, ids[0], f"/api/intents/{intent_id}/complete")
        try:
            from concurrent.futures import wait
            assert not wait([future], timeout=1.5).done
            # 成交正在等物品时不能已持有意向锁，否则与下架操作构成锁环。
            holder.scalar(select(TradeIntent).where(TradeIntent.id == intent_id).with_for_update(nowait=True))
            holder.rollback()
            assert future.result(timeout=10) == 0
        finally:
            holder.rollback()


def test_two_completions_only_one_wins(trade_data):
    item_id, ids = trade_data
    with SessionLocal() as db:
        intents = [TradeIntent(item_id=item_id, buyer_id=uid, seller_id=ids[0], status="accepted")
                   for uid in ids[1:]]
        db.add_all(intents)
        db.commit()
        intent_ids = [t.id for t in intents]
    barrier = threading.Barrier(2)

    def complete(intent_id):
        barrier.wait(timeout=5)
        return request(ids[0], f"/api/intents/{intent_id}/complete")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete, iid) for iid in intent_ids]
        codes = [f.result(timeout=15) for f in futures]
    assert sorted(codes) == [0, 40904]
    with SessionLocal() as db:
        states = db.scalars(select(TradeIntent.status).where(TradeIntent.item_id == item_id)).all()
        assert sorted(states) == ["completed", "rejected"]
        assert db.get(Content, item_id).status == "offline"
        assert db.get(Item, item_id).sold_at is not None
