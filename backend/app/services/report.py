from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.models import AnalysisResult, RecurringGroup, UploadSession
from app.pipeline.insight_types import deserialize_insights
from app.schemas.analytics import AnalyticsResponse

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _inr(amount: float) -> str:
    s = f"{amount:,.2f}"
    parts = s.split(".")
    whole = parts[0].replace(",", "")
    if len(whole) <= 3:
        formatted = whole
    else:
        last3 = whole[-3:]
        rest = whole[:-3]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        formatted = ",".join(groups + [last3]) if groups else last3
    return f"₹{formatted}" + (f".{parts[1]}" if len(parts) > 1 else "")


def build_report_context(db: Session, session: UploadSession) -> dict:
    result = db.query(AnalysisResult).filter(AnalysisResult.session_id == session.id).first()
    if not result:
        raise ValueError("Analysis not found")

    metrics = AnalyticsResponse(**json.loads(result.metrics))
    insights = deserialize_insights(result.insights)
    groups = db.query(RecurringGroup).filter(RecurringGroup.session_id == session.id).all()

    return {
        "title": "RupeeRadar Spending Report",
        "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        "filename": session.filename,
        "period_start": metrics.period_start,
        "period_end": metrics.period_end,
        "transaction_count": metrics.transaction_count,
        "total_income": _inr(metrics.total_income),
        "total_spend": _inr(metrics.total_spend),
        "savings": _inr(metrics.savings),
        "savings_rate": f"{metrics.savings_rate}%" if metrics.savings_rate is not None else "—",
        "recurring_total": _inr(metrics.recurring_total_monthly),
        "top_categories": [
            {
                "category": c.category,
                "amount": _inr(c.amount),
                "count": c.count,
                "pct": round((c.amount / metrics.total_spend * 100), 1) if metrics.total_spend else 0,
            }
            for c in metrics.top_categories
        ],
        "monthly_spend": [
            {"month": m.month, "amount": _inr(m.amount)} for m in metrics.monthly_spend
        ],
        "insights": [{"text": i.text, "source": i.source} for i in insights],
        "recurring_groups": [
            {
                "label": g.label,
                "category": g.category,
                "frequency": g.frequency,
                "typical_amount": _inr(float(g.typical_amount)),
            }
            for g in groups
        ],
        "biggest_debit": (
            {
                "description": metrics.biggest_debit.description_clean,
                "date": metrics.biggest_debit.date,
                "amount": _inr(abs(metrics.biggest_debit.amount)),
                "category": metrics.biggest_debit.category,
            }
            if metrics.biggest_debit
            else None
        ),
    }


def render_report_html(db: Session, session: UploadSession) -> str:
    context = build_report_context(db, session)
    template = _env.get_template("report.html")
    return template.render(**context)


def render_report_pdf(html: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html).write_pdf()
