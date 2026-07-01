from dataclasses import dataclass
from datetime import date

from app.models.enums import Category
from app.pipeline.cleaner import CleanedTransaction
from app.pipeline.recurring import RecurringGroupResult


@dataclass
class CategoryTotal:
    category: str
    amount: float
    count: int


@dataclass
class BiggestTransaction:
    id: str
    date: str
    description_clean: str
    amount: float
    category: str


@dataclass
class MonthlySpend:
    month: str
    amount: float


@dataclass
class MetricsResult:
    total_income: float
    total_spend: float
    savings: float
    savings_rate: float | None
    top_categories: list[CategoryTotal]
    biggest_debit: BiggestTransaction | None
    transaction_count: int
    period_start: str | None
    period_end: str | None
    monthly_spend: list[MonthlySpend]
    recurring_total_monthly: float


def compute_metrics(
    transactions: list[tuple[str, CleanedTransaction, Category, float]],
    recurring_groups: list[RecurringGroupResult] | None = None,
) -> MetricsResult:
    income = sum(txn.amount for _, txn, _, _ in transactions if txn.amount > 0)
    spend = sum(abs(txn.amount) for _, txn, _, _ in transactions if txn.amount < 0)
    savings = income - spend
    savings_rate = round((savings / income) * 100, 1) if income > 0 else None

    category_totals: dict[str, CategoryTotal] = {}
    monthly_totals: dict[str, float] = {}

    for _, txn, category, _ in transactions:
        if txn.amount < 0:
            cat = category.value
            amount = abs(txn.amount)
            if cat not in category_totals:
                category_totals[cat] = CategoryTotal(category=cat, amount=0.0, count=0)
            category_totals[cat].amount += amount
            category_totals[cat].count += 1

            month_key = txn.date[:7]
            monthly_totals[month_key] = monthly_totals.get(month_key, 0.0) + amount

    top_categories = sorted(category_totals.values(), key=lambda c: c.amount, reverse=True)
    monthly_spend = [
        MonthlySpend(month=m, amount=round(monthly_totals[m], 2))
        for m in sorted(monthly_totals.keys())
    ]

    debits = [(tid, txn, cat) for tid, txn, cat, _ in transactions if txn.amount < 0]
    biggest: BiggestTransaction | None = None
    if debits:
        tid, txn, cat = max(debits, key=lambda x: abs(x[1].amount))
        biggest = BiggestTransaction(
            id=tid,
            date=txn.date,
            description_clean=txn.description_clean,
            amount=abs(txn.amount),
            category=cat.value,
        )

    dates = [date.fromisoformat(txn.date) for _, txn, _, _ in transactions if txn.date]
    period_start = min(dates).isoformat() if dates else None
    period_end = max(dates).isoformat() if dates else None

    recurring_total = 0.0
    if recurring_groups:
        recurring_total = sum(
            g.typical_amount for g in recurring_groups if g.frequency == "monthly"
        )

    return MetricsResult(
        total_income=round(income, 2),
        total_spend=round(spend, 2),
        savings=round(savings, 2),
        savings_rate=savings_rate,
        top_categories=top_categories,
        biggest_debit=biggest,
        transaction_count=len(transactions),
        period_start=period_start,
        period_end=period_end,
        monthly_spend=monthly_spend,
        recurring_total_monthly=round(recurring_total, 2),
    )
