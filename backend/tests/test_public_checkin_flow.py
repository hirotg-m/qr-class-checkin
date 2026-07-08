from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.helpers import admin_headers, setup_class_with_today_schedule

JST = timezone(timedelta(hours=9))


def test_class_info_shows_accepting_now(client):
    class_id, today, _ = setup_class_with_today_schedule(client)
    response = client.get(f"/public/classes/{class_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["todaySession"]["date"] == today
    assert body["todaySession"]["acceptingNow"] is True


def test_invalid_pin_rejected(client):
    class_id, _, _ = setup_class_with_today_schedule(client)
    response = client.post(f"/public/classes/{class_id}/pin", json={"pin": "0000"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_PIN"


def test_full_checkin_flow_new_participant(client):
    class_id, today, admin = setup_class_with_today_schedule(client)

    pin_resp = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"})
    assert pin_resp.status_code == 200
    checkin_token = pin_resp.json()["checkinToken"]

    checkin_resp = client.post(
        f"/public/classes/{class_id}/checkin",
        json={"checkinToken": checkin_token, "children": [{"name": "山田太郎", "grade": "小5"}], "inputBy": "self"},
    )
    assert checkin_resp.status_code == 200
    result = checkin_resp.json()["results"][0]
    assert result["status"] == "new"
    assert result["proposedName"] == "山田太郎"

    confirm_resp = client.post(
        f"/public/classes/{class_id}/checkin/confirm",
        json={
            "checkinToken": checkin_token,
            "confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}],
            "inputBy": "self",
        },
    )
    assert confirm_resp.status_code == 201
    confirmed = confirm_resp.json()["results"][0]
    assert confirmed["isNew"] is True

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    assert session_resp.status_code == 200
    participants = session_resp.json()["participants"]
    assert len(participants) == 1
    assert participants[0]["name"] == "山田太郎"
    assert participants[0]["inputBy"] == "self"


def test_second_visit_matches_existing_participant(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    pin_token = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]

    client.post(
        f"/public/classes/{class_id}/checkin",
        json={"checkinToken": pin_token, "children": [{"name": "鈴木花子", "grade": "小2"}], "inputBy": "self"},
    )
    client.post(
        f"/public/classes/{class_id}/checkin/confirm",
        json={
            "checkinToken": pin_token,
            "confirmations": [{"index": 0, "action": "create_new", "name": "鈴木花子", "grade": "小2"}],
            "inputBy": "self",
        },
    )

    pin_token_2 = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]
    checkin_resp = client.post(
        f"/public/classes/{class_id}/checkin",
        json={"checkinToken": pin_token_2, "children": [{"name": "鈴木花子", "grade": "小2"}], "inputBy": "self"},
    )
    result = checkin_resp.json()["results"][0]
    assert result["status"] == "confirmed"


def test_similar_name_returns_candidates(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    pin_token = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]

    client.post(
        f"/public/classes/{class_id}/checkin",
        json={"checkinToken": pin_token, "children": [{"name": "山田太郎", "grade": "小5"}], "inputBy": "self"},
    )
    client.post(
        f"/public/classes/{class_id}/checkin/confirm",
        json={
            "checkinToken": pin_token,
            "confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}],
            "inputBy": "self",
        },
    )

    pin_token_2 = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]
    checkin_resp = client.post(
        f"/public/classes/{class_id}/checkin",
        json={"checkinToken": pin_token_2, "children": [{"name": "山田太朗", "grade": "小5"}], "inputBy": "self"},
    )
    result = checkin_resp.json()["results"][0]
    assert result["status"] == "candidates"
    assert result["candidates"][0]["name"] == "山田太郎"


def test_batch_checkin_multiple_children_siblings(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    pin_token = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]

    checkin_resp = client.post(
        f"/public/classes/{class_id}/checkin",
        json={
            "checkinToken": pin_token,
            "children": [
                {"name": "山田太郎", "grade": "小5"},
                {"name": "山田花子", "grade": "小2"},
            ],
            "inputBy": "self",
        },
    )
    results = checkin_resp.json()["results"]
    assert len(results) == 2
    assert all(r["status"] == "new" for r in results)

    confirm_resp = client.post(
        f"/public/classes/{class_id}/checkin/confirm",
        json={
            "checkinToken": pin_token,
            "confirmations": [
                {"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"},
                {"index": 1, "action": "create_new", "name": "山田花子", "grade": "小2"},
            ],
            "inputBy": "self",
        },
    )
    assert confirm_resp.status_code == 201
    assert len(confirm_resp.json()["results"]) == 2

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    assert len(session_resp.json()["participants"]) == 2


def test_grade_not_allowed_rejects_whole_batch(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    pin_token = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]

    response = client.post(
        f"/public/classes/{class_id}/checkin",
        json={
            "checkinToken": pin_token,
            "children": [
                {"name": "山田太郎", "grade": "小5"},
                {"name": "対象外太郎", "grade": "中1"},
            ],
            "inputBy": "self",
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "GRADE_NOT_ALLOWED"
    assert body["error"]["index"] == 1


def test_outside_reception_hours_rejected(client):
    admin = admin_headers(client)
    class_id = client.post(
        "/classes", json={"name": "テスト", "targetGrades": ["小1"]}, headers=admin
    ).json()["classId"]

    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")
    start_time = (now + timedelta(hours=3)).strftime("%H:%M")
    end_time = (now + timedelta(hours=4)).strftime("%H:%M")
    client.post(
        f"/classes/{class_id}/schedule",
        json={"date": today, "startTime": start_time, "endTime": end_time},
        headers=admin,
    )
    month = now.strftime("%Y-%m")
    client.put(f"/classes/{class_id}/pin/{month}", json={"pin": "1234"}, headers=admin)

    pin_token = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]
    response = client.post(
        f"/public/classes/{class_id}/checkin",
        json={"checkinToken": pin_token, "children": [{"name": "x", "grade": "小1"}], "inputBy": "self"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "OUTSIDE_RECEPTION_HOURS"


def test_checkin_token_scoped_to_class(client):
    class_id_a, _, _ = setup_class_with_today_schedule(client)
    class_id_b, _, _ = setup_class_with_today_schedule(client)

    token_for_a = client.post(f"/public/classes/{class_id_a}/pin", json={"pin": "1234"}).json()["checkinToken"]

    response = client.post(
        f"/public/classes/{class_id_b}/checkin",
        json={"checkinToken": token_for_a, "children": [{"name": "x", "grade": "小5"}], "inputBy": "self"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_pin_rate_limited_after_10_failures(client):
    class_id, _, _ = setup_class_with_today_schedule(client)
    for _ in range(10):
        client.post(f"/public/classes/{class_id}/pin", json={"pin": "0000"})
    response = client.post(f"/public/classes/{class_id}/pin", json={"pin": "0000"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"

    # 正しいPINでも、ロック中は試せない
    response = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"})
    assert response.status_code == 429


def test_successful_pin_resets_failure_count(client):
    class_id, _, _ = setup_class_with_today_schedule(client)
    for _ in range(9):
        client.post(f"/public/classes/{class_id}/pin", json={"pin": "0000"})

    ok = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"})
    assert ok.status_code == 200

    # 直前の失敗回数がリセットされているため、まだロックされない
    response = client.post(f"/public/classes/{class_id}/pin", json={"pin": "0000"})
    assert response.status_code == 401


def test_pin_rate_limit_scoped_per_class(client):
    class_id_a, _, _ = setup_class_with_today_schedule(client)
    class_id_b, _, _ = setup_class_with_today_schedule(client)

    for _ in range(10):
        client.post(f"/public/classes/{class_id_a}/pin", json={"pin": "0000"})
    assert client.post(f"/public/classes/{class_id_a}/pin", json={"pin": "0000"}).status_code == 429

    # 別クラスのPIN試行は影響を受けない
    response = client.post(f"/public/classes/{class_id_b}/pin", json={"pin": "1234"})
    assert response.status_code == 200
