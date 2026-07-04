import re
import time
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from app.services.cron import is_valid, next_times

# --- Rate limiting ---

PER_IP_WINDOW = 60        # seconds
PER_IP_LIMIT = 30
GLOBAL_DAILY_LIMIT = 100

_ip_store: dict[str, list[float]] = {}
_global_store: list[float] = []


def _prune(store: dict | list, window: float):
    now = time.time()
    if isinstance(store, dict):
        for ip in list(store.keys()):
            store[ip] = [t for t in store[ip] if now - t < window]
            if not store[ip]:
                del store[ip]
    elif isinstance(store, list):
        store[:] = [t for t in store if now - t < window]


def check_rate_limit(request: Request):
    """Enforce 30 req/min per IP and 100 req/day global using sliding window counters."""
    now = time.time()
    ip = request.client.host if request.client else "unknown"

    # global daily — reset at UTC midnight
    today = datetime.now(timezone.utc).date()
    _prune(_global_store, 86400)
    if len(_global_store) >= GLOBAL_DAILY_LIMIT:
        raise HTTPException(429, "Daily request limit reached (100/day)")
    _global_store.append(now)

    # per-IP sliding window
    _prune(_ip_store, PER_IP_WINDOW)
    if ip not in _ip_store:
        _ip_store[ip] = []
    if len(_ip_store[ip]) >= PER_IP_LIMIT:
        raise HTTPException(429, "Too many requests per minute (30/min)")
    _ip_store[ip].append(now)


# --- Input validation ---

MAX_INPUT_CHARS = 500
REJECT_IF_NO_TIME_KEYWORD = True
TIME_KEYWORDS = {
    "every", "at", "each", "on", "in", "from", "between",
    "minute", "minutes", "hour", "hours", "day", "days",
    "week", "weeks", "month", "months", "year", "years",
    "daily", "weekly", "monthly", "yearly",
    "midnight", "noon", "am", "pm",
    "never", "always",
}
ALLOWED_CHARS_RE = re.compile(r"^[a-zA-Z0-9 .,!?:;\-/@#()&'\"\n]+$")
REPEAT_THRESHOLD = 0.4  # reject if any single char >40% of input


def validate_input(text: str) -> str:
    """Pre-LLM input checks: non-empty, length ≤500, allowed chars, time keywords, gibberish detection."""
    stripped = text.strip()

    if not stripped:
        raise HTTPException(400, "Input cannot be empty")

    if len(stripped) > MAX_INPUT_CHARS:
        raise HTTPException(400, f"Input too long (max {MAX_INPUT_CHARS} characters)")

    if not ALLOWED_CHARS_RE.match(stripped):
        raise HTTPException(400, "Input contains disallowed characters")

    if REJECT_IF_NO_TIME_KEYWORD and not any(
        kw in stripped.lower() for kw in TIME_KEYWORDS
    ):
        raise HTTPException(400, "Input does not describe a schedule")

    if max(stripped.lower().count(c) for c in set(stripped.lower())) > len(stripped) * REPEAT_THRESHOLD:
        raise HTTPException(400, "Input appears to be gibberish")

    return stripped


# --- Output validation ---

CRON_FIELD_PATTERN = re.compile(
    r"^(\*/\d+|\*|(\d+(-\d+)?)(/\d+)?)(,(\*/\d+|\*|(\d+(-\d+)?)(/\d+)?))*$"
)
FIELD_BOUNDS = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day_of_month": (1, 31),
    "month": (1, 12),
    "day_of_week": (0, 6),
}
MIN_INTERVAL_MINUTES = 5


class LlmError(Exception):
    """User-facing LLM error — the LLM identified an impossible/invalid/ambiguous schedule (400)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LlmSystemError(Exception):
    """System-level LLM error — response failed backend validation (502)."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_llm_output(result: dict) -> dict:
    """Post-LLM validation: error field → 400, missing/out-of-range fields → 502."""
    error = result.get("error")
    if error:
        raise LlmError(str(error).strip())

    missing = [f for f in ("minute", "hour", "day_of_month", "month", "day_of_week", "explanation") if f not in result]
    if missing:
        raise LlmSystemError(f"LLM response missing fields: {', '.join(missing)}")

    for field, (lo, hi) in FIELD_BOUNDS.items():
        val = str(result.get(field, "")).strip()
        if not CRON_FIELD_PATTERN.match(val):
            raise LlmSystemError(f"Invalid cron syntax in field '{field}': {val!r}")
        for token in re.findall(r"\d+", val):
            if not (lo <= int(token) <= hi):
                raise LlmSystemError(
                    f"Value out of range in '{field}': {token} (allowed {lo}-{hi})"
                )

    explanation = (result.get("explanation") or "").strip()
    if not explanation or len(explanation) > 200:
        raise LlmSystemError("Explanation is missing or too long")

    return result


def check_cron_safety(cron_expr: str) -> str | None:
    """Return a warning string if the expression fires more often than every 5 minutes."""
    if not is_valid(cron_expr):
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    times = next_times(cron_expr, n=2)
    if len(times) >= 2:
        fmt = "%Y-%m-%d %H:%M UTC"
        t0 = datetime.strptime(times[0], fmt)
        t1 = datetime.strptime(times[1], fmt)
        gap = (t1 - t0).total_seconds() / 60
        if gap < MIN_INTERVAL_MINUTES:
            return (
                f"Schedule runs every {gap:.0f} minute(s) — "
                f"consider a minimum of {MIN_INTERVAL_MINUTES} min to avoid frequent runs"
            )
    return None
