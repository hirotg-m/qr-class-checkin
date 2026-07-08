from __future__ import annotations

from tests.helpers import admin_headers, setup_class_with_today_schedule, viewer_headers


def test_proxy_checkin_by_instructor(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    viewer = viewer_headers(client)

    resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy",
        json={"children": [{"name": "代理太郎", "grade": "小5"}]},
        headers=viewer,
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "new"

    confirm_resp = client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={"confirmations": [{"index": 0, "action": "create_new", "name": "代理太郎", "grade": "小5"}]},
        headers=viewer,
    )
    assert confirm_resp.status_code == 201

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    participant = session_resp.json()["participants"][0]
    assert participant["name"] == "代理太郎"
    assert participant["inputBy"] == "proxy"


def test_session_participants_sorted_by_grade(client):
    class_id, today, admin = setup_class_with_today_schedule(client, target_grades=["小5", "小2", "小1"])
    viewer = viewer_headers(client)

    client.post(
        f"/classes/{class_id}/sessions/{today}/proxy/confirm",
        json={
            "confirmations": [
                {"index": 0, "action": "create_new", "name": "五年太郎", "grade": "小5"},
                {"index": 1, "action": "create_new", "name": "一年花子", "grade": "小1"},
                {"index": 2, "action": "create_new", "name": "二年次郎", "grade": "小2"},
            ]
        },
        headers=viewer,
    )

    session_resp = client.get(f"/classes/{class_id}/sessions/{today}", headers=admin)
    grades = [p["grade"] for p in session_resp.json()["participants"]]
    assert grades == ["小1", "小2", "小5"]


def test_stats_participants_by_grade(client):
    class_id, today, admin = setup_class_with_today_schedule(client)
    pin_token = client.post(f"/public/classes/{class_id}/pin", json={"pin": "1234"}).json()["checkinToken"]

    client.post(
        f"/public/classes/{class_id}/checkin",
        json={
            "checkinToken": pin_token,
            "children": [{"name": "統計太郎", "grade": "小5"}, {"name": "統計花子", "grade": "小2"}],
            "inputBy": "self",
        },
    )
    client.post(
        f"/public/classes/{class_id}/checkin/confirm",
        json={
            "checkinToken": pin_token,
            "confirmations": [
                {"index": 0, "action": "create_new", "name": "統計太郎", "grade": "小5"},
                {"index": 1, "action": "create_new", "name": "統計花子", "grade": "小2"},
            ],
            "inputBy": "self",
        },
    )

    response = client.get(
        f"/classes/{class_id}/stats/participants",
        params={"from": today, "to": today},
        headers=admin,
    )
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["total"] == 2
    assert entries[0]["byGrade"] == {"小5": 1, "小2": 1}
