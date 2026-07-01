from dataclasses import dataclass
import json


@dataclass
class InsightItem:
    text: str
    source: str = "template"  # "template" | "ai"


def serialize_insights(items: list[InsightItem]) -> str:
    return json.dumps([{"text": item.text, "source": item.source} for item in items])


def deserialize_insights(raw: str) -> list[InsightItem]:
    data = json.loads(raw)
    if not data:
        return []
    if isinstance(data[0], str):
        return [InsightItem(text=text, source="template") for text in data]
    return [InsightItem(text=item["text"], source=item.get("source", "template")) for item in data]
