"""Tests for LLM categorization response parsing."""

from app.models.enums import Category
from app.services.llm import parse_categorization_response


def test_parse_valid_response():
    raw = {
        "transactions": [
            {"id": "abc-1", "category": "Food", "confidence": 0.85},
            {"id": "abc-2", "category": "Travel", "confidence": 0.72},
        ]
    }
    result = parse_categorization_response(raw)
    assert result["abc-1"] == (Category.FOOD, 0.85)
    assert result["abc-2"] == (Category.TRAVEL, 0.72)


def test_parse_invalid_category_defaults_to_other():
    raw = {"transactions": [{"id": "x", "category": "Groceries", "confidence": 0.9}]}
    result = parse_categorization_response(raw)
    assert result["x"][0] == Category.OTHER


def test_parse_clamps_confidence():
    raw = {"transactions": [{"id": "x", "category": "Bills", "confidence": 1.5}]}
    result = parse_categorization_response(raw)
    assert result["x"][1] == 1.0


def test_parse_empty_or_malformed():
    assert parse_categorization_response(None) == {}
    assert parse_categorization_response({"bad": "data"}) == {}
    assert parse_categorization_response({"transactions": "not a list"}) == {}
