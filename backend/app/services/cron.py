from datetime import datetime, timezone

from croniter import croniter

CRON_FIELDS = ["minute", "hour", "day_of_month", "month", "day_of_week"]


def compose(fields: dict) -> str:
    parts = []
    for field in CRON_FIELDS:
        val = fields.get(field, "*")
        if not val or val.strip() == "":
            val = "*"
        parts.append(str(val).strip())
    return " ".join(parts)


def is_valid(expr: str) -> bool:
    return croniter.is_valid(expr)


def next_times(expr: str, n: int = 5, base: datetime | None = None) -> list[str]:
    if base is None:
        base = datetime.now(timezone.utc)
    cron = croniter(expr, base)
    return [
        cron.get_next(datetime).strftime("%Y-%m-%d %H:%M UTC")
        for _ in range(n)
    ]
