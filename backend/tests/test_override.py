from pathlib import Path

from fastapi.testclient import TestClient


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hdfc_messy.csv"


def test_category_override_recomputes_analytics(client: TestClient):
    with FIXTURE_PATH.open("rb") as f:
        response = client.post(
            "/api/v1/upload",
            files={"file": ("hdfc_messy.csv", f, "text/csv")},
        )
    session_id = response.json()["session_id"]

    txns = client.get(f"/api/v1/sessions/{session_id}/transactions?page_size=100")
    other_txn = next((t for t in txns.json()["items"] if t["category"] == "Other"), None)
    if not other_txn:
        other_txn = txns.json()["items"][0]

    before = client.get(f"/api/v1/sessions/{session_id}/analytics").json()

    patch = client.patch(
        f"/api/v1/sessions/{session_id}/transactions/{other_txn['id']}",
        json={"category": "Shopping"},
    )
    assert patch.status_code == 200
    updated = patch.json()["transaction"]
    assert updated["category"] == "Shopping"
    assert updated["category_overridden"] is True
    assert updated["category_confidence"] == 1.0

    after = client.get(f"/api/v1/sessions/{session_id}/analytics").json()
    assert after["top_categories"] != before["top_categories"] or after != before
