from pathlib import Path

from fastapi.testclient import TestClient

EMI_FIXTURE = Path(__file__).parent / "fixtures" / "hdfc_with_emi.csv"


def test_recurring_detection_on_emi_fixture(client: TestClient):
    with EMI_FIXTURE.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("hdfc_with_emi.csv", f, "text/csv")},
        )

    assert response.status_code == 200
    session_id = response.json()["session_id"]

    recurring = client.get(f"/api/v1/sessions/{session_id}/recurring")
    assert recurring.status_code == 200
    data = recurring.json()

    assert len(data["groups"]) >= 3
    assert data["recurring_total_monthly"] > 0

    labels = {g["label"].upper() for g in data["groups"]}
    assert any("NETFLIX" in l or "SPOTIFY" in l for l in labels)
    assert any("EMI" in l or "HOME LOAN" in l for l in labels)

    insights = client.get(f"/api/v1/sessions/{session_id}/insights").json()
    insight_texts = [i["text"] for i in insights["insights"]]
    assert any("recurring" in t.lower() for t in insight_texts)
    assert len(insights["insights"]) >= 4

    analytics = client.get(f"/api/v1/sessions/{session_id}/analytics").json()
    assert len(analytics["monthly_spend"]) >= 3
    assert analytics["recurring_total_monthly"] > 0
