from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services import guard
from app.services.langfuse_client import score_trace, is_available

router = APIRouter()


class FeedbackRequest(BaseModel):
    trace_id: str
    rating: str  # "positive" | "negative"
    comment: str = ""


class FeedbackResponse(BaseModel):
    id: str


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    req: FeedbackRequest,
    _=Depends(guard.check_rate_limit),
):
    if not is_available():
        raise HTTPException(400, "Feedback requires Langfuse to be configured")

    if not req.trace_id:
        raise HTTPException(400, "trace_id is required")

    if req.rating not in ("positive", "negative"):
        raise HTTPException(400, "rating must be 'positive' or 'negative'")

    if len(req.comment) > 500:
        raise HTTPException(400, "Comment too long (max 500 characters)")

    score_trace(
        trace_id=req.trace_id,
        name="user_rating",
        value=1.0 if req.rating == "positive" else 0.0,
        comment=req.comment,
    )

    return FeedbackResponse(id=req.trace_id)
