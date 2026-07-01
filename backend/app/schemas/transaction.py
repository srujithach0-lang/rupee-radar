from pydantic import BaseModel, Field

from app.models.enums import Category


class TransactionResponse(BaseModel):
    id: str
    date: str
    description_raw: str
    description_clean: str
    amount: float
    type: str
    balance: float | None
    category: str
    category_confidence: float
    category_overridden: bool = False
    is_recurring: bool = False
    payment_mode: str | None
    merchant: str | None


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class TransactionCategoryUpdate(BaseModel):
    category: Category


class TransactionUpdateResponse(BaseModel):
    transaction: TransactionResponse
    analytics_updated: bool = True
