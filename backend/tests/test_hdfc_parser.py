from pathlib import Path

from app.parsers.hdfc import HdfcCsvParser


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hdfc_messy.csv"


def test_hdfc_parser_reads_fixture():
    parser = HdfcCsvParser()
    content = FIXTURE_PATH.read_bytes()
    assert parser.can_parse("hdfc_messy.csv", content)

    with FIXTURE_PATH.open("rb") as f:
        result = parser.parse(f, "hdfc_messy.csv")

    assert len(result.transactions) >= 50
    assert all(t.date for t in result.transactions)
    assert all(t.description_raw for t in result.transactions)
    assert any(t.amount < 0 for t in result.transactions)
    assert any(t.amount > 0 for t in result.transactions)
