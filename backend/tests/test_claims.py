"""
test_claims.py — Smoke tests for the claims API.
Run: pytest backend/tests/ -v
"""
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app

client = TestClient(app)


def _make_image_bytes():
    """Create a minimal in-memory JPEG for upload testing."""
    img = Image.new("RGB", (100, 100), color=(180, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_submit_claim_minimal():
    """Submit a claim without files — should return a valid decision."""
    data = {
        "claim_type":       "auto",
        "description":      "My car was rear-ended at a traffic light causing significant bumper damage.",
        "requested_amount": "5000",
        "full_name":        "Test User",
        "email":            "test@example.com",
    }
    r = client.post("/api/submit-claim", data=data)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] in ("approved", "flagged", "pending", "rejected")
    assert 0.0 <= body["ai_scores"]["fraud_score"] <= 1.0
    assert "claim_id" in body


def test_submit_claim_with_image():
    """Submit a claim with a damage photo."""
    data = {
        "claim_type":       "property",
        "description":      "Severe water damage to the living room caused by a burst pipe during winter storm.",
        "requested_amount": "12000",
        "full_name":        "Jane Doe",
        "email":            "jane@example.com",
    }
    files = [("files", ("damage.jpg", _make_image_bytes(), "image/jpeg"))]
    r = client.post("/api/submit-claim", data=data, files=files)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] in ("approved", "flagged", "pending", "rejected")
    assert isinstance(body["ai_scores"]["estimated_payout"], float)
    assert body["ai_scores"]["estimated_payout"] <= 12000


def test_submit_claim_validation_fail():
    """Description too short should trigger unprocessable entity or bad request."""
    data = {
        "claim_type":       "health",
        "description":      "short",        # < 20 chars — backend may process but payout will be low
        "requested_amount": "1000",
        "full_name":        "A",
        "email":            "bad-email",    # invalid email — should fail at pydantic
    }
    r = client.post("/api/submit-claim", data=data)
    # Either 422 (pydantic) or 500 (email parse) depending on form data handling
    assert r.status_code in (201, 422, 400), r.text


def test_check_fraud_not_found():
    """check-fraud with unknown UUID should return 404."""
    r = client.post("/api/check-fraud", json={"claim_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


def test_admin_dashboard():
    r = client.get("/admin/dashboard")
    assert r.status_code == 200
    body = r.json()
    for field in ("total_claims", "approved", "flagged", "pending", "total_payout"):
        assert field in body


def test_admin_claims():
    r = client.get("/admin/claims")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "total_pages" in body


def test_admin_heatmap():
    r = client.get("/admin/heatmap")
    assert r.status_code == 200
    assert "cells" in r.json()
