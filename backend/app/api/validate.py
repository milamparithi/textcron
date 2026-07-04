from fastapi import APIRouter

from app.models.schemas import ValidateRequest, ValidateResponse
from app.services import cron

router = APIRouter()


@router.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest):
    """Validate a cron expression and return next scheduled times."""
    valid = cron.is_valid(req.cron)
    explanation = ""
    next_times = []

    if valid:
        next_times = cron.next_times(req.cron)
        explanation = f"Next run at {next_times[0]}"
    else:
        explanation = "Invalid cron expression"

    return ValidateResponse(
        valid=valid,
        explanation=explanation,
        next_times=next_times,
    )
