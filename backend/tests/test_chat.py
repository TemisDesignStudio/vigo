import pytest
from fastapi.testclient import TestClient
from urllib.error import URLError

import main
from main import app, sessions


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("VIGO_DB_PATH", str(tmp_path / "vigo.db"))
    sessions.clear()
    yield
    sessions.clear()


def test_chat_returns_controlled_reply_with_fixed_model(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_request(messages, api_key):
        assert api_key == "test-key"
        assert messages[-1].content == "2+2 چند می‌شود؟"
        return "۲+۲ برابر با ۴ است."

    monkeypatch.setattr(main, "request_openrouter", fake_request)
    response = TestClient(app).post("/api/chat", json={"messages": [{"role": "user", "content": "2+2 چند می‌شود؟"}]})

    assert response.status_code == 200
    assert response.json() == {"message": "۲+۲ برابر با ۴ است."}
    assert main.OPENROUTER_MODEL == "openrouter/free"


def test_chat_returns_persian_error_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = TestClient(app).post("/api/chat", json={"messages": [{"role": "user", "content": "سلام"}]})

    assert response.status_code == 503
    assert "کلید OpenRouter" in response.json()["detail"]


def test_chat_validates_history_and_upstream_error(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    invalid = TestClient(app).post("/api/chat", json={"messages": [{"role": "assistant", "content": "سلام"}]})
    assert invalid.status_code == 422

    monkeypatch.setattr(main, "request_openrouter", lambda *_: (_ for _ in ()).throw(main.OpenRouterError()))
    unavailable = TestClient(app).post("/api/chat", json={"messages": [{"role": "user", "content": "سلام"}]})
    assert unavailable.status_code == 503
    assert "اتصال به سرویس" in unavailable.json()["detail"]


def test_chat_retries_a_transient_openrouter_failure(monkeypatch) -> None:
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return '{"choices":[{"message":{"content":"پاسخ آزمایشی"}}]}'.encode()

    def flaky_urlopen(*_, **__):
        calls.append(True)
        if len(calls) == 1:
            raise URLError("temporary network issue")
        return Response()

    monkeypatch.setattr(main, "urlopen", flaky_urlopen)
    monkeypatch.setattr(main.time, "sleep", lambda _: None)
    reply = main.request_openrouter([main.ChatMessage(role="user", content="سلام")], "test-key")

    assert reply == "پاسخ آزمایشی"
    assert len(calls) == 2
