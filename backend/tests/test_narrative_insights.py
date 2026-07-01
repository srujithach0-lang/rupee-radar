from app.services.llm import parse_narrative_response


def test_parse_narrative_response():
    raw = {"insights": ["Food is 30% of spend.", "Consider reviewing subscriptions."]}
    result = parse_narrative_response(raw)
    assert len(result) == 2
    assert "Food" in result[0]


def test_parse_narrative_response_empty():
    assert parse_narrative_response(None) == []
    assert parse_narrative_response({}) == []
