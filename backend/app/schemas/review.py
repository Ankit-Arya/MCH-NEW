from pydantic import BaseModel
from app.models.all_models import ReviewAction


class ReviewIn(BaseModel):
    action: ReviewAction
    comments: str | None = None
    recommended_penalty_amount: float | None = None
    final_penalty_amount: float | None = None


class ReviewOut(BaseModel):
    id: int
    inspection_id: int
    reviewer_id: int
    reviewer_role: str
    review_level: str
    action: ReviewAction
    comments: str | None = None
    recommended_penalty_amount: float | None = None
    final_penalty_amount: float | None = None
    model_config = {"from_attributes": True}
