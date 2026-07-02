import pytest
from app.services import guard
from app.services.llm import LlmResult


VALID_LLM_RESPONSE = LlmResult(
    parsed={
        "minute": "0", "hour": "15",
        "day_of_month": "*", "month": "*", "day_of_week": "1-5",
        "explanation": "At 3:00 PM, Monday through Friday",
    },
    model="test-model",
    prompt_tokens=50,
    completion_tokens=10,
    total_tokens=60,
)


def llm_result(parsed: dict) -> LlmResult:
    return LlmResult(parsed=parsed, model="test-model")


@pytest.fixture(autouse=True)
def reset_rate_limits():
    guard._ip_store.clear()
    guard._global_store.clear()


@pytest.fixture
def mock_llm(monkeypatch):
    def fake(text):
        return LlmResult(dict(VALID_LLM_RESPONSE.parsed), model="test-model")
    monkeypatch.setattr("app.services.llm.translate", fake)


class TestTranslate:
    def test_success(self, client, mock_llm):
        resp = client.post("/api/translate", json={"text": "every weekday at 3pm"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["cron"] == "0 15 * * 1-5"
        assert body["warning"] == ""
        assert body["explanation"] == "At 3:00 PM, Monday through Friday"

    def test_empty_body_422(self, client):
        resp = client.post("/api/translate", json={})
        assert resp.status_code == 422

    def test_llm_error_400(self, client, monkeypatch):
        def fake(text):
            return llm_result({"error": "February never has 30 days"})
        monkeypatch.setattr("app.services.llm.translate", fake)

        resp = client.post("/api/translate", json={"text": "every feb 30"})
        assert resp.status_code == 400
        assert "February" in resp.json()["detail"]

    def test_llm_system_error_502(self, client, monkeypatch):
        def fake(text):
            return llm_result({
                "minute": "99", "hour": "*", "day_of_month": "*",
                "month": "*", "day_of_week": "*", "explanation": "test",
            })
        monkeypatch.setattr("app.services.llm.translate", fake)

        resp = client.post("/api/translate", json={"text": "bad data"})
        assert resp.status_code == 502

    def test_frequent_schedule_warning(self, client, monkeypatch):
        def fake(text):
            return llm_result({
                "minute": "*", "hour": "*", "day_of_month": "*",
                "month": "*", "day_of_week": "*",
                "explanation": "Every minute",
            })
        monkeypatch.setattr("app.services.llm.translate", fake)

        resp = client.post("/api/translate", json={"text": "every minute"})
        assert resp.status_code == 200
        assert "warning" in resp.json()
        assert resp.json()["warning"] != ""

    def test_invalid_input_400(self, client, mock_llm):
        resp = client.post("/api/translate", json={"text": "<script>alert(1)</script>"})
        assert resp.status_code == 400
