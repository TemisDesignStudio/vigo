import json

import pytest
from fastapi.testclient import TestClient

import main
from main import app, sessions


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGO_DB_PATH", str(tmp_path / "vigo.db"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    sessions.clear()
    yield
    sessions.clear()


def admin_client() -> TestClient:
    client = TestClient(app)
    assert client.post("/api/auth/login", json={"username": "user", "password": "password"}).status_code == 200
    return client


def ask(client: TestClient) -> dict:
    response = client.post("/api/admin/assistant", json={"messages": [{"role": "user", "content": "دستور مدیر"}]})
    assert response.status_code == 200
    return response.json()


def test_admin_assistant_creates_updates_and_changes_status(monkeypatch) -> None:
    client = admin_client()
    outputs = iter([
        {"message": "کمپین ثبت شد.", "operation": {"action": "create", "resource": "campaign", "data": {"brand_name": "ویگو", "requester_name": "سارا", "contact": "sara@example.com", "budget": 5000000, "objective": "معرفی محصول"}}},
        {"message": "هدف به‌روزرسانی شد.", "operation": {"action": "update", "resource": "campaign", "record_id": 1, "data": {"objective": "فروش"}}},
        {"message": "وضعیت به‌روزرسانی شد.", "operation": {"action": "status", "resource": "campaign", "record_id": 1, "data": {"status": "reviewing"}}},
    ])
    monkeypatch.setattr(main, "request_admin_assistant", lambda *_: json.dumps(next(outputs)))

    created = ask(client)
    assert created["change"]["record"]["brand_name"] == "ویگو"
    updated = ask(client)
    assert updated["change"]["record"]["objective"] == "فروش"
    status_changed = ask(client)
    assert status_changed["change"]["record"]["status"] == "reviewing"


def test_invalid_assistant_output_never_changes_data(monkeypatch) -> None:
    client = admin_client()
    invalid_outputs = [
        {"message": "حذف می‌کنم.", "operation": {"action": "delete", "resource": "campaign", "record_id": 1, "data": {}}},
        {"message": "وضعیت را عوض می‌کنم.", "operation": {"action": "status", "resource": "campaign", "record_id": 1, "data": {"status": "unknown"}}},
        {"message": "رکورد می‌سازم.", "operation": {"action": "create", "resource": "campaign", "data": {"brand_name": "ویگو"}}},
    ]
    for output in invalid_outputs:
        monkeypatch.setattr(main, "request_admin_assistant", lambda *_args, value=output: json.dumps(value))
        response = client.post("/api/admin/assistant", json={"messages": [{"role": "user", "content": "دستور مدیر"}]})
        assert response.status_code == 502
        assert client.get("/api/admin/campaigns").json() == []


def test_public_user_cannot_use_admin_assistant() -> None:
    response = TestClient(app).post("/api/admin/assistant", json={"messages": [{"role": "user", "content": "یک کمپین بساز"}]})
    assert response.status_code == 401


def test_admin_assistant_resolves_unique_campaign_name_and_id(monkeypatch) -> None:
    client = admin_client()
    campaign = client.post("/api/admin/campaigns", json={"brand_name": "Temis Branding", "requester_name": "سارا", "contact": "sara@example.com", "budget": 5000000, "objective": "معرفی"}).json()
    monkeypatch.setattr(main, "request_admin_assistant", lambda *_: pytest.fail("وضعیت صریح نباید به مدل وابسته باشد"))
    response = client.post("/api/admin/assistant", json={"messages": [{"role": "user", "content": "وضعیت کمپین Temis Branding را به active تغییر بده"}]})
    assert response.status_code == 200
    assert response.json()["change"]["record"]["status"] == "active"

    response = client.post("/api/admin/assistant", json={"messages": [{"role": "user", "content": f"وضعیت کمپین شماره {campaign['id']} را به active تغییر بده"}]})
    assert response.status_code == 200
    context = main.admin_context()
    assert main.resolve_admin_references(f"وضعیت کمپین شماره {campaign['id']} را به active تغییر بده", context)["resolved"][0]["reason"] == "explicit_id"


def test_admin_assistant_requires_id_for_duplicate_campaign_names(monkeypatch) -> None:
    client = admin_client()
    payload = {"brand_name": "Temis Branding", "requester_name": "سارا", "contact": "sara@example.com", "budget": 5000000, "objective": "معرفی"}
    client.post("/api/admin/campaigns", json=payload)
    client.post("/api/admin/campaigns", json={**payload, "requester_name": "رضا"})
    monkeypatch.setattr(main, "request_admin_assistant", lambda *_: pytest.fail("مدل نباید برای نام مبهم فراخوانی شود"))

    response = client.post("/api/admin/assistant", json={"messages": [{"role": "user", "content": "وضعیت کمپین Temis Branding را تغییر بده"}]})
    assert response.status_code == 200
    assert response.json()["change"] is None
    assert "شناسه" in response.json()["message"]


def test_admin_assistant_normalizes_fenced_common_operation_format(monkeypatch) -> None:
    client = admin_client()
    campaign = client.post("/api/admin/campaigns", json={"brand_name": "Temis Branding", "requester_name": "سارا", "contact": "sara@example.com", "budget": 5000000, "objective": "معرفی"}).json()
    raw = f'''```json
{{"message":"وضعیت تغییر کرد.","operation":{{"type":"change_status","record_type":"campaigns","id":{campaign["id"]},"status":"active"}}}}
```'''
    monkeypatch.setattr(main, "request_admin_assistant", lambda *_: raw)

    response = client.post("/api/admin/assistant", json={"messages": [{"role": "user", "content": "دستور مدیریتی"}]})
    assert response.status_code == 200
    assert response.json()["change"]["record"]["status"] == "active"
