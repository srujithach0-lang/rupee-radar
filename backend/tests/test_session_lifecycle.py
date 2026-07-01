from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models import UploadSession


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hdfc_messy.csv"


def _upload_fixture(client: TestClient) -> str:
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("hdfc_messy.csv", f, "text/csv")},
        )
    return response.json()["session_id"]


def test_delete_session_removes_data(client: TestClient, db_session):
    session_id = _upload_fixture(client)
    response = client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 204

    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404
    assert db_session.query(UploadSession).filter(UploadSession.id == session_id).first() is None


def test_expired_session_returns_404(client: TestClient, db_session):
    session_id = _upload_fixture(client)
    session = db_session.query(UploadSession).filter(UploadSession.id == session_id).first()
    session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404


def test_report_html_endpoint(client: TestClient):
    session_id = _upload_fixture(client)
    response = client.get(f"/api/v1/sessions/{session_id}/report?format=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "RupeeRadar" in response.text
    assert "₹" in response.text
