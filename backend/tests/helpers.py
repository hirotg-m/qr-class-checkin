from __future__ import annotations

from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def admin_headers(client) -> dict:
    token = client.post("/auth/login", json={"code": "99999999"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def viewer_headers(client) -> dict:
    token = client.post("/auth/login", json={"code": "11111111"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def setup_class_with_today_schedule(client, target_grades: list[str] | None = None) -> tuple[str, str, dict]:
    """今すぐ受付中となるクラス・本日の活動予定・当月PINを作成するテスト用ヘルパー。"""
    admin = admin_headers(client)
    create_resp = client.post(
        "/classes",
        json={
            "name": "テストクラス",
            "description": "",
            "targetGrades": target_grades or ["小5", "小2"],
        },
        headers=admin,
    )
    class_id = create_resp.json()["classId"]

    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")
    start_time = (now - timedelta(minutes=15)).strftime("%H:%M")
    end_time = (now + timedelta(minutes=60)).strftime("%H:%M")
    client.post(
        f"/classes/{class_id}/schedule",
        json={"date": today, "startTime": start_time, "endTime": end_time, "location": "体育館"},
        headers=admin,
    )
    month = now.strftime("%Y-%m")
    client.put(f"/classes/{class_id}/pin/{month}", json={"pin": "1234"}, headers=admin)
    return class_id, today, admin
