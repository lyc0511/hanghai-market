import json

from sqlalchemy import select

from app.models import AuditLog
from tests.conftest import call


def test_student_password_recovery(client, db, make_user):
    _, admin = make_user(role="admin")
    credentials = {"student_no": "29961111", "password": "Initial1234"}
    registered = call(client, "POST", "/auth/register", json={**credentials, "nickname": "找回测试"})["data"]
    user_id = registered["user"]["id"]
    old_headers = {"Authorization": "Bearer " + registered["access_token"]}
    url = f"/admin/users/{user_id}/reset-password"

    assert call(client, "POST", url, old_headers, json={"identity_verified": True})["code"] == 40300
    assert call(client, "POST", url, admin, json={"identity_verified": False})["code"] == 40000
    reset = client.post("/api" + url, headers=admin, json={"identity_verified": True})
    assert reset.headers["cache-control"] == "no-store"
    temporary = reset.json()["data"]["temporary_password"]
    assert call(client, "GET", "/auth/me", old_headers)["code"] == 40100
    assert call(client, "POST", "/auth/login", json=credentials)["code"] == 40101

    def login(password):
        result = call(client, "POST", "/auth/login", json={**credentials, "password": password})
        assert result["code"] == 0
        return result["data"]

    limited = login(temporary)
    assert limited["user"]["must_change_password"] is True
    headers = {"Authorization": "Bearer " + limited["access_token"]}
    assert call(client, "GET", "/auth/me", headers)["data"]["must_change_password"] is True
    assert call(client, "GET", "/intents/mine", headers)["code"] == 40300
    assert call(client, "PATCH", "/auth/me", headers, json={"nickname": "不能绕过"})["code"] == 40300
    assert call(client, "POST", "/auth/password", headers, json={"old_password": temporary, "new_password": temporary})["code"] != 0

    # 再次生成会使第一次临时密码和相应登录都失效。
    second = call(client, "POST", url, admin, json={"identity_verified": True})["data"]["temporary_password"]
    assert second != temporary
    assert call(client, "GET", "/auth/me", headers)["code"] == 40100
    assert call(client, "POST", "/auth/login", json={**credentials, "password": temporary})["code"] == 40101
    limited = login(second)
    headers = {"Authorization": "Bearer " + limited["access_token"]}
    assert call(client, "POST", "/auth/password", headers, json={"old_password": second, "new_password": "Recovered1234"})["code"] == 0
    assert call(client, "GET", "/auth/me", headers)["code"] == 40100
    assert call(client, "POST", "/auth/login", json={**credentials, "password": second})["code"] == 40101
    normal = login("Recovered1234")
    assert normal["user"]["must_change_password"] is False
    assert call(client, "GET", "/intents/mine", {"Authorization": "Bearer " + normal["access_token"]})["code"] == 0
    logs = db.scalars(select(AuditLog).where(AuditLog.target_id == user_id, AuditLog.action == "reset_password")).all()
    assert len(logs) == 2
    assert all(log.detail == {"identity_verified": True} for log in logs)
    assert temporary not in json.dumps([log.detail for log in logs])


def test_reset_protects_admin_and_banned_accounts(client, db, make_user):
    owner, admin = make_user(role="admin")
    other_admin, _ = make_user(role="admin")
    banned, _ = make_user()
    banned.status = "banned"
    db.flush()
    for target, expected in [(owner, 40371), (other_admin, 40371), (banned, 40971)]:
        assert call(client, "POST", f"/admin/users/{target.id}/reset-password", admin,
                    json={"identity_verified": True})["code"] == expected
