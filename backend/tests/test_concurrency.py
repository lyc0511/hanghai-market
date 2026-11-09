"""并发测试：活动只剩 1 个名额时，多人同时报名，只能有 1 人成功、报名人数不能超。

这个测试必须让多个数据库连接真正提交（行锁只在不同事务之间起作用），
所以不用 conftest 里的回滚夹具，而是自己造临时数据，结束后在 finally 里全部删掉。
"""
import threading
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models import Activity, ActivitySignup, Club, Content, Notification, User

N = 8  # 同时报名的人数


def test_last_seat_only_one_wins():
    db = SessionLocal()
    user_ids: list[int] = []
    activity_id = None
    try:
        club = db.scalar(select(Club).limit(1))
        users = [User(student_no=f"2998{i:04d}", nickname=f"并发{i}", password_hash="x") for i in range(N)]
        db.add_all(users)
        db.flush()
        user_ids = [u.id for u in users]

        start = datetime.now(timezone.utc) + timedelta(days=3)
        c = Content(type="activity", owner_id=club.president_id or users[0].id, title="并发测试活动", status="online")
        db.add(c)
        db.flush()
        activity_id = c.id
        db.add(Activity(content_id=c.id, club_id=club.content_id, start_time=start, end_time=start + timedelta(hours=2),
                        location="测试教室", capacity=1))
        db.commit()

        tokens = [create_access_token(uid)[0] for uid in user_ids]
        barrier = threading.Barrier(N)
        codes: list[int] = []
        lock = threading.Lock()

        def worker(token: str) -> None:
            client = TestClient(app)
            barrier.wait()  # 所有线程到齐后同时发请求
            r = client.post(f"/api/activities/{activity_id}/signup", headers={"Authorization": f"Bearer {token}"})
            with lock:
                codes.append(r.json()["code"])

        threads = [threading.Thread(target=worker, args=(t,)) for t in tokens]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert sorted(codes) == [0] + [40941] * (N - 1), codes
        db.expire_all()
        assert db.get(Activity, activity_id).enrolled_count == 1
        signed = db.scalars(select(ActivitySignup).where(ActivitySignup.activity_id == activity_id)).all()
        assert len(signed) == 1
    finally:
        db.rollback()
        if activity_id:
            db.execute(delete(ActivitySignup).where(ActivitySignup.activity_id == activity_id))
            db.execute(delete(Activity).where(Activity.content_id == activity_id))
            db.execute(delete(Content).where(Content.id == activity_id))
        if user_ids:
            db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()
        db.close()


def test_signup_waits_for_row_lock():
    """确定性验证行锁：事务 A 锁住活动并占掉最后一个名额但先不提交，
    此时 B 的报名请求必须阻塞等待；A 提交后 B 才继续，并看到「名额已满」。
    如果去掉 with_for_update，B 会先读到旧的报名人数（0）并通过名额检查，最终也报名成功
    （enrolled_count 被写成 1，实际却有 2 人报名，即超卖）—— 本测试就会失败。
    """
    from app.api.activities import lock_activity

    db = SessionLocal()
    holder = SessionLocal()
    user_ids: list[int] = []
    activity_id = None
    try:
        club = db.scalar(select(Club).limit(1))
        users = [User(student_no=f"2997{i:04d}", nickname=f"锁测试{i}", password_hash="x") for i in range(2)]
        db.add_all(users)
        db.flush()
        user_ids = [u.id for u in users]
        start = datetime.now(timezone.utc) + timedelta(days=3)
        c = Content(type="activity", owner_id=users[0].id, title="行锁测试活动", status="online")
        db.add(c)
        db.flush()
        activity_id = c.id
        db.add(Activity(content_id=c.id, club_id=club.content_id, start_time=start, end_time=start + timedelta(hours=2),
                        location="测试教室", capacity=1))
        db.commit()

        # A：拿到行锁，占掉唯一的名额，暂不提交
        _, a = lock_activity(holder, activity_id)
        holder.add(ActivitySignup(activity_id=activity_id, user_id=user_ids[0], status="signed"))
        a.enrolled_count = 1
        holder.flush()

        result: dict = {}
        token = create_access_token(user_ids[1])[0]

        def b_signup() -> None:
            r = TestClient(app).post(f"/api/activities/{activity_id}/signup", headers={"Authorization": f"Bearer {token}"})
            result["code"] = r.json()["code"]

        t = threading.Thread(target=b_signup)
        t.start()
        t.join(timeout=1.5)
        assert t.is_alive(), "B 没有等待行锁就返回了"

        holder.commit()  # A 提交，释放锁
        t.join(timeout=10)
        assert result.get("code") == 40941
        db.expire_all()
        assert db.get(Activity, activity_id).enrolled_count == 1
    finally:
        holder.rollback()
        holder.close()
        db.rollback()
        if activity_id:
            db.execute(delete(ActivitySignup).where(ActivitySignup.activity_id == activity_id))
            db.execute(delete(Activity).where(Activity.content_id == activity_id))
            db.execute(delete(Content).where(Content.id == activity_id))
        if user_ids:
            db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()
        db.close()
