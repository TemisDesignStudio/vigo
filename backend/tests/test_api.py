import sqlite3

import pytest
from fastapi.testclient import TestClient

from main import app, sessions


CAMPAIGN = {
    "brand_name": "Vigo",
    "requester_name": "سارا",
    "contact": "sara@example.com",
    "budget": 5000000,
    "objective": "معرفی محصول",
    "start_date": "2026-11-20",
    "end_date": "2026-11-25",
    "description": "توضیحات آزمایشی",
}

COLLABORATION = {
    "name": "آرمان",
    "contact": "09121234567",
    "social_network": "Instagram",
    "profile_url": "https://instagram.com/arman",
    "activity_field": "فناوری",
}


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGO_DB_PATH", str(tmp_path / "vigo.db"))
    sessions.clear()
    yield
    sessions.clear()


def logged_in_client() -> TestClient:
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "user", "password": "password"}).status_code == 200
    return client


def test_database_is_created_with_schema(tmp_path, monkeypatch) -> None:
    database = tmp_path / "vigo.db"
    monkeypatch.setenv("VIGO_DB_PATH", str(database))

    assert logged_in_client().get("/api/admin/campaigns").status_code == 200
    assert database.is_file()
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {"users", "campaigns", "collaboration_requests"} <= tables


def test_public_campaign_requires_valid_data() -> None:
    client = TestClient(app)
    invalid = client.post("/api/campaigns", json={**CAMPAIGN, "budget": -1})
    assert invalid.status_code == 422
    assert invalid.json()["detail"] == "اطلاعات ارسالی نامعتبر است."

    created = client.post("/api/campaigns", json=CAMPAIGN)
    assert created.status_code == 201
    assert created.json()["status"] == "new"


def test_admin_campaign_crud_without_delete() -> None:
    client = TestClient(app)
    assert client.get("/api/admin/campaigns").status_code == 401

    client = logged_in_client()
    created = client.post("/api/admin/campaigns", json=CAMPAIGN)
    assert created.status_code == 201
    campaign_id = created.json()["id"]
    assert client.get(f"/api/admin/campaigns/{campaign_id}").status_code == 200
    assert client.patch(f"/api/admin/campaigns/{campaign_id}", json={"objective": "فروش"}).json()["objective"] == "فروش"
    assert client.patch(f"/api/admin/campaigns/{campaign_id}/status", json={"status": "active"}).json()["status"] == "active"
    assert client.patch(f"/api/admin/campaigns/{campaign_id}/status", json={"status": "unknown"}).status_code == 422
    assert all("delete" not in methods for methods in app.openapi()["paths"].values())


def test_admin_collaboration_crud() -> None:
    client = logged_in_client()
    created = client.post("/api/admin/collaboration-requests", json=COLLABORATION)
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert client.get("/api/admin/collaboration-requests").json()[0]["id"] == record_id
    assert client.patch(f"/api/admin/collaboration-requests/{record_id}", json={"activity_field": "سبک زندگی"}).json()["activity_field"] == "سبک زندگی"
    assert client.patch(f"/api/admin/collaboration-requests/{record_id}/status", json={"status": "approved"}).json()["status"] == "approved"
    assert client.patch(f"/api/admin/collaboration-requests/{record_id}/status", json={"status": "active"}).status_code == 422
