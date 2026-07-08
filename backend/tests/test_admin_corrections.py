from __future__ import annotations

from tests.helpers import setup_class_with_today_schedule, viewer_headers


def test_viewer_proxy_rejected_outside_reception_window(client):
    class_id, _today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)
    past_date = "2000-01-01"

    resp = client.post(
        f"/classes/{class_id}/sessions/{past_date}/proxy",
        json={"children": [{"name": "過去太郎", "grade": "小5"}]},
        headers=viewer,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "OUTSIDE_RECEPTION_HOURS"


def test_admin_proxy_bypasses_reception_window_for_past_date(client):
    class_id, _today, admin = setup_class_with_today_schedule(client)
    past_date = "2000-01-01"

    resp = client.post(
        f"/classes/{class_id}/sessions/{past_date}/proxy",
        json={"children": [{"name": "過去太郎", "grade": "小5"}]},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "new"

    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{past_date}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "過去太郎", "grade": "小5"}]},
        headers=admin,
    )
    assert confirm_resp.status_code == 201

    session_resp = client.get(f"/classes/{class_id}/sessions/{past_date}", headers=admin)
    participant = session_resp.json()["participants"][0]
    assert participant["name"] == "過去太郎"
    assert participant["inputBy"] == "proxy"


def test_admin_can_delete_session_participant(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    client.post(
        f"/classes/{class_id}/sessions/{today}/proxy",
        json={"children": [{"name": "削除太郎", "grade": "小5"}]},
        headers=viewer,
    )
    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "削除太郎", "grade": "小5"}]},
        headers=viewer,
    )
    participant_id = confirm_resp.json()["results"][0]["participantId"]

    delete_resp = client.delete(
        f"/classes/{class_id}/sessions/{today}/participants/{participant_id}", headers=admin
    )
    assert delete_resp.status_code == 204

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    assert session_resp.json()["participants"] == []


def test_viewer_cannot_delete_session_participant(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    resp = client.delete(
        f"/classes/{class_id}/sessions/{today}/participants/nonexistent", headers=viewer
    )
    assert resp.status_code == 403


def test_admin_can_update_participant_name_and_grade(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    client.post(
        f"/classes/{class_id}/sessions/{today}/proxy",
        json={"children": [{"name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    participant_id = confirm_resp.json()["results"][0]["participantId"]

    update_resp = client.put(
        f"/classes/{class_id}/participants/{participant_id}",
        json={"name": "山田次郎", "grade": "小2"},
        headers=admin,
    )
    assert update_resp.status_code == 200
    assert update_resp.json() == {
        "participantId": participant_id,
        "name": "山田次郎",
        "grade": "小2",
        "firstSeenDate": today,
    }

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    participant = session_resp.json()["participants"][0]
    assert participant["name"] == "山田次郎"
    assert participant["grade"] == "小2"


def test_session_participant_shows_visit_count_and_previous_date(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)
    past_date = "2000-01-01"

    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    participant_id = confirm_resp.json()["results"][0]["participantId"]

    client.post(
        f"/classes/{class_id}/sessions/{past_date}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "select_existing", "participantId": participant_id}]},
        headers=admin,
    )

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    participant = session_resp.json()["participants"][0]
    assert participant["visitCount"] == 1
    assert participant["previousDate"] == past_date

    past_session_resp = client.get(f"/classes/{class_id}/sessions/{past_date}", headers=admin)
    past_participant = past_session_resp.json()["participants"][0]
    assert past_participant["visitCount"] == 0
    assert past_participant["previousDate"] is None


def test_update_participant_rejects_disallowed_grade(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    client.post(
        f"/classes/{class_id}/sessions/{today}/proxy",
        json={"children": [{"name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    participant_id = confirm_resp.json()["results"][0]["participantId"]

    resp = client.put(
        f"/classes/{class_id}/participants/{participant_id}",
        json={"name": "山田太郎", "grade": "中1"},
        headers=admin,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "GRADE_NOT_ALLOWED"


def test_list_participants_sorted_by_grade_and_name(client):
    class_id, today, admin = setup_class_with_today_schedule(client, target_grades=["小5", "小2"])
    viewer = viewer_headers(client)

    client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={
            "confirmations": [
                {"index": 0, "action": "create_new", "name": "山田花子", "grade": "小2"},
                {"index": 1, "action": "create_new", "name": "山田太郎", "grade": "小5"},
                {"index": 2, "action": "create_new", "name": "佐藤次郎", "grade": "小2"},
            ]
        },
        headers=viewer,
    )

    resp = client.get(f"/classes/{class_id}/participants", headers=viewer)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names == ["佐藤次郎", "山田花子", "山田太郎"]
    assert all(p["visitCount"] == 1 for p in resp.json())
    assert all(p["firstSeenDate"] == today for p in resp.json())


def test_admin_can_delete_participant_from_roster(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    participant_id = confirm_resp.json()["results"][0]["participantId"]

    delete_resp = client.delete(f"/classes/{class_id}/participants/{participant_id}", headers=admin)
    assert delete_resp.status_code == 204

    list_resp = client.get(f"/classes/{class_id}/participants", headers=admin)
    assert list_resp.json() == []

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    assert session_resp.json()["participants"] == []


def test_viewer_cannot_delete_participant_from_roster(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "山田太郎", "grade": "小5"}]},
        headers=viewer,
    )
    participant_id = confirm_resp.json()["results"][0]["participantId"]

    resp = client.delete(f"/classes/{class_id}/participants/{participant_id}", headers=viewer)
    assert resp.status_code == 403
