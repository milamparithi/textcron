import os
import uuid
from datetime import datetime, timezone

_lf = None
_available = False


def get_client():
    """Return the Langfuse singleton client, or a noop client if keys are missing."""
    global _lf, _available
    if _lf is not None:
        return _lf
    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = os.getenv("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        _available = False
        _lf = _NoopClient()
        return _lf
    try:
        from langfuse import Langfuse
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        _lf = Langfuse(public_key=pk, secret_key=sk, host=host)
        _available = True
    except Exception:
        _lf = _NoopClient()
        _available = False
    return _lf


def is_available() -> bool:
    """Check whether a real Langfuse client has been initialised."""
    get_client()
    return _available


def create_trace(name: str, input: dict | None = None) -> str:
    """Create a Langfuse trace via ingestion API. Returns trace ID (or empty string if unavailable)."""
    """Create a Langfuse trace via the direct ingestion API.
    Returns the trace ID (or empty string if Langfuse is unavailable)."""
    lf = get_client()
    if not _available:
        return ""
    trace_id = lf.create_trace_id()
    ts = datetime.now(timezone.utc).isoformat()
    from langfuse.api.ingestion.types.ingestion_event import IngestionEvent_TraceCreate
    from langfuse.api.ingestion.types.trace_body import TraceBody
    body = TraceBody(id=trace_id, name=name, input=input)
    event = IngestionEvent_TraceCreate(body=body, id=trace_id, timestamp=ts)
    lf.api.ingestion.batch(batch=[event])
    return trace_id


def create_generation(
    trace_id: str,
    name: str,
    model: str,
    input_data: any = None,
    output: any = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    input_cost: float = 0.0,
    output_cost: float = 0.0,
    total_cost: float = 0.0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    level: str = "DEFAULT",
    status_message: str = "",
):
    """Record an LLM generation observation against a trace via ingestion API."""
    trace_id: str,
    name: str,
    model: str,
    input_data: any = None,
    output: any = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    input_cost: float = 0.0,
    output_cost: float = 0.0,
    total_cost: float = 0.0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    level: str = "DEFAULT",
    status_message: str = "",
):
    lf = get_client()
    if not _available:
        return
    from langfuse.api.ingestion.types import ObservationType
    from langfuse.api.ingestion.types.ingestion_event import (
        IngestionEvent_ObservationCreate,
        ObservationBody,
    )
    from langfuse.api.commons.types.observation_level import ObservationLevel
    from langfuse.api.commons.types.usage import Usage

    obs_id = lf.create_trace_id()
    now = datetime.now(timezone.utc)
    body = ObservationBody(
        id=obs_id,
        trace_id=trace_id,
        type=ObservationType.GENERATION,
        name=name,
        model=model or None,
        start_time=start_time or now,
        end_time=end_time,
        input=input_data,
        output=output,
        level=ObservationLevel(level) if level else None,
        status_message=status_message or None,
        usage=Usage(
            input=prompt_tokens,
            output=completion_tokens,
            total=total_tokens or (prompt_tokens + completion_tokens),
            unit="TOKENS",
            input_cost=input_cost or None,
            output_cost=output_cost or None,
            total_cost=total_cost or None,
        ),
    )
    ts = now.isoformat()
    event = IngestionEvent_ObservationCreate(body=body, id=obs_id, timestamp=ts)
    lf.api.ingestion.batch(batch=[event])


def score_trace(trace_id: str, name: str, value: float, comment: str = ""):
    """Attach a score (e.g. user rating) to an existing trace. Skips comment when empty."""
    lf = get_client()
    if not _available:
        return
    kwargs = dict(trace_id=trace_id, name=name, value=value)
    if comment:
        kwargs["comment"] = comment
    lf.create_score(**kwargs)
    lf.flush()


class _NoopClient:
    """Stand-in client when Langfuse is not configured — all calls are no-ops."""

    def get_current_trace_id(self):
        return None

    def create_score(self, **kwargs):
        pass

    def create_trace_id(self):
        return str(uuid.uuid4())

    def flush(self):
        pass

    @property
    def api(self):
        return _NoopAPI()


class _NoopAPI:
    """Stand-in for Langfuse API client — returns empty ingestion responses."""
    class _Ingestion:
        def batch(self, **kwargs):
            from langfuse.api.ingestion.types.ingestion_response import IngestionResponse
            return IngestionResponse(successes=[], errors=[])

    @property
    def ingestion(self):
        return self._Ingestion()
