import time
import pytest
from fastapi import HTTPException
from app.services.guard import (
    validate_input,
    validate_llm_output,
    check_cron_safety,
    check_rate_limit,
    LlmError,
    LlmSystemError,
)

# ── Input validation ──────────────────────────────────────────────


class TestValidateInput:
    def test_valid_input_passes(self):
        assert validate_input("every weekday at 3pm") == "every weekday at 3pm"

    def test_empty_raises(self):
        with pytest.raises(HTTPException, match="cannot be empty"):
            validate_input("   ")

    def test_too_long_raises(self):
        with pytest.raises(HTTPException, match="too long"):
            validate_input("a" * 501)

    def test_disallowed_chars_raises(self):
        with pytest.raises(HTTPException, match="disallowed characters"):
            validate_input("<script>alert('xss')</script>")

    def test_no_time_keyword_raises(self):
        with pytest.raises(HTTPException, match="does not describe a schedule"):
            validate_input("hello world")

    def test_gibberish_raises(self):
        with pytest.raises(HTTPException, match="gibberish"):
            validate_input("every aaaaaaaa")


# ── Output validation ─────────────────────────────────────────────


class TestValidateLlmOutput:
    def test_valid_output_passes(self):
        result = validate_llm_output({
            "minute": "0", "hour": "15", "day_of_month": "*",
            "month": "*", "day_of_week": "1-5", "explanation": "test",
        })
        assert result["minute"] == "0"

    def test_error_field_raises_llm_error(self):
        with pytest.raises(LlmError, match="February never has 30 days"):
            validate_llm_output({"error": "February never has 30 days"})

    def test_missing_fields_raises_system_error(self):
        with pytest.raises(LlmSystemError, match="missing fields"):
            validate_llm_output({"minute": "0"})

    def test_out_of_range_raises_system_error(self):
        with pytest.raises(LlmSystemError, match="Value out of range"):
            validate_llm_output({
                "minute": "99", "hour": "*", "day_of_month": "*",
                "month": "*", "day_of_week": "*", "explanation": "test",
            })

    def test_invalid_syntax_raises_system_error(self):
        with pytest.raises(LlmSystemError, match="Invalid cron syntax"):
            validate_llm_output({
                "minute": "abc", "hour": "*", "day_of_month": "*",
                "month": "*", "day_of_week": "*", "explanation": "test",
            })

    def test_missing_explanation_raises_system_error(self):
        with pytest.raises(LlmSystemError, match="Explanation is missing"):
            validate_llm_output({
                "minute": "0", "hour": "*", "day_of_month": "*",
                "month": "*", "day_of_week": "*", "explanation": "",
            })


# ── Cron safety ───────────────────────────────────────────────────


class TestCheckCronSafety:
    def test_frequent_returns_warning(self):
        warning = check_cron_safety("* * * * *")
        assert warning is not None
        assert "every 1 minute" in warning

    def test_infrequent_returns_none(self):
        assert check_cron_safety("0 15 * * 1-5") is None

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid cron"):
            check_cron_safety("bad")


# ── Rate limiting ─────────────────────────────────────────────────


class FakeRequest:
    def __init__(self, host="127.0.0.1"):
        self.client = type("obj", (object,), {"host": host})()


class TestCheckRateLimit:
    def test_first_request_passes(self):
        check_rate_limit(FakeRequest())

    def test_many_requests_from_same_ip_fails(self):
        from app.services import guard
        guard._ip_store.clear()
        guard._global_store.clear()

        ip = "10.0.0.1"
        # fill per-IP limit
        now = time.time()
        guard._ip_store[ip] = [now - 2] * (guard.PER_IP_LIMIT - 1)

        # should pass (at limit - 1 + 1 = limit, which is OK since check is >=)
        # Actually we need to check: the guard checks len >= PER_IP_LIMIT
        # So if we have PER_IP_LIMIT entries, the next request will fail
        # Let's set up PER_IP_LIMIT - 1 entries, then one more passes, one more fails
        with pytest.raises(HTTPException, match="Too many requests"):
            check_rate_limit(FakeRequest(host=ip))
            check_rate_limit(FakeRequest(host=ip))
