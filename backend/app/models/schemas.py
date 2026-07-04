from pydantic import BaseModel


class TranslateRequest(BaseModel):
    """Natural language schedule input, optional timezone."""

    text: str
    timezone: str = "UTC"


class TranslateResponse(BaseModel):
    """Successful translation result with cron expression and trace ID."""

    cron: str
    text: str
    explanation: str
    warning: str = ""
    trace_id: str = ""


class ValidateRequest(BaseModel):
    """Raw cron expression to validate."""

    cron: str


class ValidateResponse(BaseModel):
    """Validation result with next scheduled times."""

    valid: bool
    explanation: str
    next_times: list[str]


class ExplainRequest(BaseModel):
    """Cron expression to explain in plain text."""

    cron: str


class ExplainResponse(BaseModel):
    """Plain-text explanation of a cron expression."""

    explanation: str


class ErrorResponse(BaseModel):
    """Generic error response with detail message."""

    detail: str
