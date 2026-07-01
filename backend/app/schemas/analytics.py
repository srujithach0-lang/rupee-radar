from pydantic import BaseModel, Field


class CategoryTotalResponse(BaseModel):
    category: str
    amount: float
    count: int


class BiggestTransactionResponse(BaseModel):
    id: str
    date: str
    description_clean: str
    amount: float
    category: str


class MonthlySpendResponse(BaseModel):
    month: str
    amount: float


class AnalyticsResponse(BaseModel):
    total_income: float
    total_spend: float
    savings: float
    savings_rate: float | None
    top_categories: list[CategoryTotalResponse]
    biggest_debit: BiggestTransactionResponse | None
    transaction_count: int
    period_start: str | None
    period_end: str | None
    monthly_spend: list[MonthlySpendResponse] = Field(default_factory=list)
    recurring_total_monthly: float = 0.0


class InsightItemResponse(BaseModel):
    text: str
    source: str = "template"


class InsightsResponse(BaseModel):
    insights: list[InsightItemResponse] = Field(default_factory=list)
