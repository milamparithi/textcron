from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    timezone: str = "UTC"


class TranslateResponse(BaseModel):
    cron: str
    text: str
    explanation: str
    warning: str = ""
    trace_id: str = ""


class ValidateRequest(BaseModel):
    cron: str


class ValidateResponse(BaseModel):
    valid: bool
    explanation: str
    next_times: list[str]


class ExplainRequest(BaseModel):
    cron: str


class ExplainResponse(BaseModel):
    explanation: str


class ErrorResponse(BaseModel):
    detail: str
