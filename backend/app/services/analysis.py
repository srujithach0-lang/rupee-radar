import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AnalysisResult, RecurringGroup, Transaction, UploadSession
from app.models.enums import Category
from app.pipeline.cleaner import CleanedTransaction
from app.pipeline.insight_types import serialize_insights
from app.pipeline.insights import generate_insights
from app.pipeline.metrics import MetricsResult, compute_metrics
from app.pipeline.recurring import RecurringGroupResult, detect_recurring


def _txn_to_cleaned(txn: Transaction) -> CleanedTransaction:
    from app.models.enums import TransactionType

    return CleanedTransaction(
        date=txn.date.isoformat(),
        description_raw=txn.description_raw,
        description_clean=txn.description_clean,
        amount=float(txn.amount),
        type=TransactionType(txn.type),
        balance=float(txn.balance) if txn.balance is not None else None,
        payment_mode=txn.payment_mode,
        merchant=txn.merchant,
        is_duplicate=txn.is_duplicate,
    )


def _metrics_to_json(metrics: MetricsResult) -> dict:
    return {
        "total_income": metrics.total_income,
        "total_spend": metrics.total_spend,
        "savings": metrics.savings,
        "savings_rate": metrics.savings_rate,
        "top_categories": [
            {"category": c.category, "amount": round(c.amount, 2), "count": c.count}
            for c in metrics.top_categories
        ],
        "biggest_debit": {
            "id": metrics.biggest_debit.id,
            "date": metrics.biggest_debit.date,
            "description_clean": metrics.biggest_debit.description_clean,
            "amount": metrics.biggest_debit.amount,
            "category": metrics.biggest_debit.category,
        }
        if metrics.biggest_debit
        else None,
        "transaction_count": metrics.transaction_count,
        "period_start": metrics.period_start,
        "period_end": metrics.period_end,
        "monthly_spend": [{"month": m.month, "amount": m.amount} for m in metrics.monthly_spend],
        "recurring_total_monthly": metrics.recurring_total_monthly,
    }


def persist_recurring_groups(
    db: Session,
    session_id: str,
    groups: list[RecurringGroupResult],
) -> None:
    db.query(RecurringGroup).filter(RecurringGroup.session_id == session_id).delete()
    db.query(Transaction).filter(Transaction.session_id == session_id).update(
        {"is_recurring": False, "recurring_group_id": None}
    )

    recurring_txn_ids: set[str] = set()
    for group in groups:
        db.add(
            RecurringGroup(
                id=group.id,
                session_id=session_id,
                label=group.label,
                category=group.category,
                frequency=group.frequency,
                typical_amount=group.typical_amount,
                last_seen_date=datetime.strptime(group.last_seen_date, "%Y-%m-%d").date(),
                transaction_ids=json.dumps(group.transaction_ids),
                confidence=group.confidence,
            )
        )
        recurring_txn_ids.update(group.transaction_ids)

    for txn_id in recurring_txn_ids:
        txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if txn:
            group = next((g for g in groups if txn_id in g.transaction_ids), None)
            txn.is_recurring = True
            txn.recurring_group_id = group.id if group else None


def recompute_analysis(db: Session, session: UploadSession) -> MetricsResult:
    """Recompute metrics and insights from persisted transactions."""
    txns = db.query(Transaction).filter(Transaction.session_id == session.id).all()
    txn_tuples: list[tuple[str, CleanedTransaction, Category, float]] = [
        (t.id, _txn_to_cleaned(t), Category(t.category), t.category_confidence) for t in txns
    ]

    recurring_results = detect_recurring(txn_tuples)
    persist_recurring_groups(db, session.id, recurring_results)

    metrics = compute_metrics(txn_tuples, recurring_results)
    insights = generate_insights(metrics, recurring_results)

    metrics_json = _metrics_to_json(metrics)
    existing = db.query(AnalysisResult).filter(AnalysisResult.session_id == session.id).first()
    if existing:
        existing.metrics = json.dumps(metrics_json)
        existing.insights = serialize_insights(insights)
        existing.generated_at = datetime.utcnow()
    else:
        db.add(
            AnalysisResult(
                session_id=session.id,
                metrics=json.dumps(metrics_json),
                insights=serialize_insights(insights),
            )
        )

    db.commit()
    return metrics
