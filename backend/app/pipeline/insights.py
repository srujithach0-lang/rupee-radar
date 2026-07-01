from app.pipeline.insight_types import InsightItem
from app.pipeline.metrics import MetricsResult
from app.pipeline.recurring import RecurringGroupResult
from app.services.llm import generate_narrative_insights, get_llm_service


def _inr(amount: float) -> str:
    """Format amount in Indian numbering style."""
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


def generate_template_insights(
    metrics: MetricsResult,
    recurring_groups: list[RecurringGroupResult] | None = None,
) -> list[InsightItem]:
    insights: list[InsightItem] = []

    if metrics.top_categories:
        top = metrics.top_categories[0]
        insights.append(
            InsightItem(
                text=f"You spent {_inr(top.amount)} on {top.category} — your largest spending category."
            )
        )

    if metrics.biggest_debit:
        b = metrics.biggest_debit
        insights.append(
            InsightItem(
                text=f"Your biggest transaction was {_inr(b.amount)} to {b.description_clean} on {b.date}."
            )
        )

    if metrics.period_start and metrics.period_end:
        insights.append(
            InsightItem(
                text=(
                    f"Total spend for {metrics.period_start} to {metrics.period_end} "
                    f"was {_inr(metrics.total_spend)}."
                )
            )
        )
    elif metrics.total_spend > 0:
        insights.append(
            InsightItem(text=f"Your total spend for this statement was {_inr(metrics.total_spend)}.")
        )

    if metrics.savings_rate is not None:
        insights.append(
            InsightItem(
                text=(
                    f"You saved {_inr(metrics.savings)} ({metrics.savings_rate}% of income) "
                    "over this period."
                )
            )
        )

    if recurring_groups:
        monthly_groups = [g for g in recurring_groups if g.frequency == "monthly"]
        if monthly_groups:
            count = len(monthly_groups)
            total = metrics.recurring_total_monthly
            insights.append(
                InsightItem(text=f"You have {count} recurring payments totalling {_inr(total)}/month.")
            )

    return insights


def generate_insights(
    metrics: MetricsResult,
    recurring_groups: list[RecurringGroupResult] | None = None,
) -> list[InsightItem]:
    template_insights = generate_template_insights(metrics, recurring_groups)
    if not template_insights:
        return [InsightItem(text="Upload a statement with transactions to see personalized insights.")]

    llm = get_llm_service()
    narrative = generate_narrative_insights(metrics, recurring_groups, llm=llm)
    return template_insights + narrative
