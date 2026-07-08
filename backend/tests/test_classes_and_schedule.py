from __future__ import annotations

from tests.helpers import admin_headers, viewer_headers


def test_create_list_update_delete_class(client):
    admin = admin_headers(client)

    create_resp = client.post(
        "/classes",
        json={"name": "サッカークラス", "description": "説明", "targetGrades": ["小1", "小2"]},
        headers=admin,
    )
    assert create_resp.status_code == 201
    class_id = create_resp.json()["classId"]

    list_resp = client.get("/classes", headers=viewer_headers(client))
    assert list_resp.status_code == 200
    assert any(c["classId"] == class_id for c in list_resp.json())

    update_resp = client.put(
        f"/classes/{class_id}",
        json={"name": "改名クラス", "description": "説明2", "targetGrades": ["小3"]},
        headers=admin,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "改名クラス"

    delete_resp = client.delete(f"/classes/{class_id}", headers=admin)
    assert delete_resp.status_code == 204

    list_after_delete = client.get("/classes", headers=admin)
    assert all(c["classId"] != class_id for c in list_after_delete.json())


def test_viewer_cannot_create_class(client):
    viewer = viewer_headers(client)
    response = client.post("/classes", json={"name": "x", "targetGrades": []}, headers=viewer)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_invalid_grade_rejected_by_schema(client):
    admin = admin_headers(client)
    response = client.post("/classes", json={"name": "x", "targetGrades": ["1年"]}, headers=admin)
    assert response.status_code == 422


def test_schedule_crud(client):
    admin = admin_headers(client)
    class_id = client.post(
        "/classes", json={"name": "テスト", "targetGrades": ["小1"]}, headers=admin
    ).json()["classId"]

    create_resp = client.post(
        f"/classes/{class_id}/schedule",
        json={"date": "2026-08-03", "startTime": "16:00", "endTime": "17:00", "location": "体育館"},
        headers=admin,
    )
    assert create_resp.status_code == 201

    duplicate_resp = client.post(
        f"/classes/{class_id}/schedule",
        json={"date": "2026-08-03", "startTime": "16:00", "endTime": "17:00", "location": "体育館"},
        headers=admin,
    )
    assert duplicate_resp.status_code == 409
    assert duplicate_resp.json()["error"]["code"] == "CONFLICT"

    list_resp = client.get(
        f"/classes/{class_id}/schedule", params={"month": "2026-08"}, headers=viewer_headers(client)
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = client.put(
        f"/classes/{class_id}/schedule/2026-08-03",
        json={"startTime": "16:30", "endTime": "17:30", "location": "第二体育館"},
        headers=admin,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["startTime"] == "16:30"

    delete_resp = client.delete(f"/classes/{class_id}/schedule/2026-08-03", headers=admin)
    assert delete_resp.status_code == 204

    list_after_delete = client.get(
        f"/classes/{class_id}/schedule", params={"month": "2026-08"}, headers=admin
    )
    assert list_after_delete.json() == []


def test_pin_set_and_get(client):
    admin = admin_headers(client)
    class_id = client.post(
        "/classes", json={"name": "テスト", "targetGrades": ["小1"]}, headers=admin
    ).json()["classId"]

    unset_resp = client.get(f"/classes/{class_id}/pin/2026-08", headers=viewer_headers(client))
    assert unset_resp.status_code == 200
    assert unset_resp.json() == {"classId": class_id, "month": "2026-08", "pin": None}

    set_resp = client.put(f"/classes/{class_id}/pin/2026-08", json={"pin": "1234"}, headers=admin)
    assert set_resp.status_code == 200

    get_resp = client.get(f"/classes/{class_id}/pin/2026-08", headers=viewer_headers(client))
    assert get_resp.json() == {"classId": class_id, "month": "2026-08", "pin": "1234"}


def test_viewer_cannot_set_pin(client):
    admin = admin_headers(client)
    class_id = client.post(
        "/classes", json={"name": "テスト", "targetGrades": ["小1"]}, headers=admin
    ).json()["classId"]

    resp = client.put(
        f"/classes/{class_id}/pin/2026-08", json={"pin": "1234"}, headers=viewer_headers(client)
    )
    assert resp.status_code == 403
