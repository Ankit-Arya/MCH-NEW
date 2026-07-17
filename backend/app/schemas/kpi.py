from pydantic import BaseModel


class MonthlyCalculationRequest(BaseModel):
    billing_cycle_id: int
    contract_id: int


class MonthlyCalculationResponse(BaseModel):
    contract_id: int
    billing_cycle_id: int
    average_score: float
    is_penalty_applicable: bool
    penalty_amount: float
    approved_inspection_count: int = 0
    pending_gm_decision_count: int = 0
