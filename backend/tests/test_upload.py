from pathlib import Path

from fastapi.testclient import TestClient


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hdfc_messy.csv"


def test_upload_fixture_end_to_end(client: TestClient):
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("hdfc_messy.csv", f, "text/csv")},
        )

    assert response.status_code == 200
    session_id = response.json()["session_id"]

    session = client.get(f"/api/v1/sessions/{session_id}")
    assert session.status_code == 200
    assert session.json()["status"] == "ready"
    assert session.json()["row_count"] >= 50

    analytics = client.get(f"/api/v1/sessions/{session_id}/analytics")
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["total_spend"] > 0
    assert len(data["top_categories"]) > 0

    insights = client.get(f"/api/v1/sessions/{session_id}/insights")
    assert insights.status_code == 200
    insight_items = insights.json()["insights"]
    assert len(insight_items) >= 3
    assert all("text" in i for i in insight_items)

    txns = client.get(f"/api/v1/sessions/{session_id}/transactions")
    assert txns.status_code == 200
    assert txns.json()["total"] >= 50

    recurring = client.get(f"/api/v1/sessions/{session_id}/recurring")
    assert recurring.status_code == 200
    recurring_data = recurring.json()
    assert "groups" in recurring_data
    assert recurring_data["recurring_total_monthly"] >= 0

    analytics_data = analytics.json()
    assert "monthly_spend" in analytics_data
    assert "recurring_total_monthly" in analytics_data


def test_upload_rejects_unsupported_file(client: TestClient):
    response = client.post(
        "/api/v1/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_categorization_coverage_on_fixture(client: TestClient):
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("hdfc_messy.csv", f, "text/csv")},
        )
    session_id = response.json()["session_id"]
    txns = client.get(f"/api/v1/sessions/{session_id}/transactions?page_size=100")
    items = txns.json()["items"]
    non_other = [t for t in items if t["category"] != "Other"]
    ratio = len(non_other) / len(items)
    assert ratio >= 0.70
