import pytest
from app.services.cron import compose, is_valid, next_times


class TestCompose:
    def test_joins_all_fields(self):
        result = compose({
            "minute": "0", "hour": "15",
            "day_of_month": "*", "month": "*", "day_of_week": "1-5",
        })
        assert result == "0 15 * * 1-5"

    def test_defaults_missing_field_to_star(self):
        result = compose({
            "minute": "*/5", "hour": "*",
            "day_of_month": "*", "month": "*",
        })
        assert result == "*/5 * * * *"

    def test_defaults_empty_string_to_star(self):
        result = compose({
            "minute": "0", "hour": "",
            "day_of_month": "*", "month": "*", "day_of_week": "*",
        })
        assert result == "0 * * * *"

    def test_defaults_none_to_star(self):
        assert compose({"minute": "0"}) == "0 * * * *"


class TestIsValid:
    def test_valid_expression(self):
        assert is_valid("0 15 * * 1-5") is True

    def test_invalid_expression(self):
        assert is_valid("not-a-cron") is False

    def test_empty_string(self):
        assert is_valid("") is False


class TestNextTimes:
    def test_returns_exact_count(self):
        times = next_times("*/15 * * * *", n=3)
        assert len(times) == 3

    def test_each_entry_is_formatted(self):
        times = next_times("0 15 * * *", n=1)
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC", times[0])

    def test_times_are_increasing(self):
        times = next_times("*/5 * * * *", n=4)
        for i in range(1, len(times)):
            assert times[i] > times[i - 1]

    def test_custom_base(self):
        from datetime import datetime, timezone, timedelta
        base = datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)
        times = next_times("0 0 * * *", n=1, base=base)
        assert times[0] == "2026-01-01 00:00 UTC"

    def test_invalid_expression_raises(self):
        from croniter import CroniterBadCronError
        with pytest.raises((ValueError, CroniterBadCronError)):
            next_times("bad", n=1)
