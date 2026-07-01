from app.pipeline.insight_types import InsightItem, deserialize_insights, serialize_insights
from app.pipeline.insights import generate_template_insights
from app.pipeline.metrics import MetricsResult, CategoryTotal, BiggestTransaction


def test_insight_serialization_roundtrip():
    items = [InsightItem(text="Hello", source="template"), InsightItem(text="AI tip", source="ai")]
    raw = serialize_insights(items)
    restored = deserialize_insights(raw)
    assert len(restored) == 2
    assert restored[1].source == "ai"


def test_deserialize_legacy_string_insights():
    import json

    raw = json.dumps(["Insight one", "Insight two"])
    items = deserialize_insights(raw)
    assert items[0].text == "Insight one"
    assert items[0].source == "template"


def test_template_insights_minimum_three():
    metrics = MetricsResult(
        total_income=100000,
        total_spend=75000,
        savings=25000,
        savings_rate=25.0,
        top_categories=[CategoryTotal(category="Food", amount=12000, count=10)],
        biggest_debit=BiggestTransaction(
            id="1",
            date="2024-11-01",
            description_clean="SWIGGY",
            amount=-500,
            category="Food",
        ),
        transaction_count=50,
        period_start="2024-11-01",
        period_end="2024-11-30",
        monthly_spend=[],
        recurring_total_monthly=0,
    )
    insights = generate_template_insights(metrics)
    assert len(insights) >= 3
