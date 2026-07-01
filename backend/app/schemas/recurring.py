from pydantic import BaseModel, Field


class RecurringGroupResponse(BaseModel):
    id: str
    label: str
    category: str
    frequency: str
    typical_amount: float
    last_seen_date: str
    transaction_ids: list[str]
    confidence: float


class RecurringListResponse(BaseModel):
    groups: list[RecurringGroupResponse] = Field(default_factory=list)
    recurring_total_monthly: float = 0.0
