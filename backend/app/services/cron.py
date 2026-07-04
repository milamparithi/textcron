from datetime import datetime, timezone

from croniter import croniter

CRON_FIELDS = ["minute", "hour", "day_of_month", "month", "day_of_week"]


def compose(fields: dict) -> str:
    """Assemble a 5-field cron expression from a dict of {minute, hour, day_of_month, month, day_of_week}."""
    parts = []
    for field in CRON_FIELDS:
        val = fields.get(field, "*")
        if not val or val.strip() == "":
            val = "*"
        parts.append(str(val).strip())
    return " ".join(parts)


def is_valid(expr: str) -> bool:
    """Check whether a cron expression is syntactically valid."""
    return croniter.is_valid(expr)


def next_times(expr: str, n: int = 5, base: datetime | None = None) -> list[str]:
    """Return the next N execution times for a cron expression as formatted strings."""
    if base is None:
        base = datetime.now(timezone.utc)
    cron = croniter(expr, base)
    return [
        cron.get_next(datetime).strftime("%Y-%m-%d %H:%M UTC")
        for _ in range(n)
    ]
