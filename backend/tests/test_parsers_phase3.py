from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.parsers.generic import GenericCsvParser
from app.parsers.icici import IciciCsvParser


ICICI_FIXTURE = Path(__file__).parent / "fixtures" / "icici_sample.csv"
GENERIC_FIXTURE = Path(__file__).parent / "fixtures" / "generic_columns.csv"


def test_icici_parser_reads_fixture():
    parser = IciciCsvParser()
    content = ICICI_FIXTURE.read_bytes()
    assert parser.can_parse("icici_sample.csv", content)

    with ICICI_FIXTURE.open("rb") as f:
        result = parser.parse(f, "icici_sample.csv")

    assert len(result.transactions) >= 15
    assert any(t.amount < 0 for t in result.transactions)
    assert any(t.amount > 0 for t in result.transactions)


def test_generic_parser_reads_fixture():
    parser = GenericCsvParser()
    content = GENERIC_FIXTURE.read_bytes()
    assert parser.can_parse("generic_columns.csv", content)

    with GENERIC_FIXTURE.open("rb") as f:
        result = parser.parse(f, "generic_columns.csv")

    assert len(result.transactions) >= 8
    assert all(t.date for t in result.transactions)


def test_upload_icici_fixture(client: TestClient):
    with ICICI_FIXTURE.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("icici_sample.csv", f, "text/csv")},
        )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    session = client.get(f"/api/v1/sessions/{session_id}")
    assert session.json()["status"] == "ready"
    assert session.json()["row_count"] >= 15


def test_upload_generic_fixture(client: TestClient):
    with GENERIC_FIXTURE.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("generic_columns.csv", f, "text/csv")},
        )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    session = client.get(f"/api/v1/sessions/{session_id}")
    assert session.json()["status"] == "ready"
