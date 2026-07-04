from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import TranslateRequest, TranslateResponse
from app.services import llm, cron, guard
from app.services.langfuse_client import create_trace, create_generation

router = APIRouter()


@router.post("/translate", response_model=TranslateResponse)
def translate(
    req: TranslateRequest,
    _=Depends(guard.check_rate_limit),
):
    """Convert natural language schedule to a valid cron expression."""
    text = guard.validate_input(req.text)

    trace_id = create_trace(name="translate", input={"text": text})

    start_time = datetime.now(timezone.utc)
    try:
        result = llm.translate(text)
    except Exception as e:
        end_time = datetime.now(timezone.utc)
        create_generation(
            trace_id=trace_id,
            name="llm_translate",
            model="",
            input_data={"text": text},
            output="",
            start_time=start_time,
            end_time=end_time,
            level="ERROR",
            status_message=str(e),
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to parse schedule. Please rephrase.",
        )

    end_time = datetime.now(timezone.utc)
    create_generation(
        trace_id=trace_id,
        name="llm_translate",
        model=result.model,
        input_data=result.prompt,
        output=result.response_text,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        input_cost=result.input_cost,
        output_cost=result.output_cost,
        total_cost=result.total_cost,
        start_time=start_time,
        end_time=end_time,
    )

    try:
        result = guard.validate_llm_output(result.parsed)
    except guard.LlmError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except guard.LlmSystemError as e:
        raise HTTPException(status_code=502, detail=e.message)

    cron_expr = cron.compose(result)

    warning = guard.check_cron_safety(cron_expr)

    return TranslateResponse(
        cron=cron_expr,
        text=req.text,
        explanation=result.get("explanation", ""),
        warning=warning or "",
        trace_id=trace_id,
    )
