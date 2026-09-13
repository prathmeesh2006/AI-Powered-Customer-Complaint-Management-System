"""
Backend test suite for AIVOA complaint management.

Covers:
1. Text complaint extraction
2. Missing fields detection
3. Follow-up batch number correction
4. Follow-up quantity correction
5. Risk assessment
6. Final QMS commit
7. API error handling

Run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────
# Test 1: Health check
# ─────────────────────────────────────────────

def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model" in data
    print(f"[OK] Health check passed. Model: {data['model']}")


# ─────────────────────────────────────────────
# Test 2: Text complaint extraction
# ─────────────────────────────────────────────

SAMPLE_COMPLAINT_1 = """
ABC Pharmacy reported discolored capsules in Amoxicillin Capsules 500 mg
from batch AMX240602. 12 capsules were affected. The complaint was reported
on September 10, 2026.
"""

def test_analyze_text_extracts_structured_fields():
    """AI should extract product name, batch, complaint type, and quantity."""
    resp = client.post("/api/complaints/analyze-text", json={"text": SAMPLE_COMPLAINT_1})
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()

    complaint = data["complaint"]
    print(f"Extracted: {complaint}")

    # Check key fields were extracted
    assert complaint.get("product_name"), "Product name should be extracted"
    assert complaint.get("batch_lot_number"), "Batch number should be extracted"
    assert data.get("copilot_message"), "Copilot message should be present"
    assert "risk" in data, "Risk assessment should be present"
    print(f"[OK] Text extraction passed. Product: {complaint.get('product_name')}, Batch: {complaint.get('batch_lot_number')}")


# ─────────────────────────────────────────────
# Test 3: Missing fields detection
# ─────────────────────────────────────────────

INCOMPLETE_COMPLAINT = """
A patient came to our counter and complained about some tablets.
The medicine tasted different than usual. We're not sure which batch it was from.
"""

def test_missing_fields_detected():
    """System should report missing fields without hallucinating values."""
    resp = client.post("/api/complaints/analyze-text", json={"text": INCOMPLETE_COMPLAINT})
    assert resp.status_code == 200
    data = resp.json()

    missing = data.get("missing_fields", [])
    complaint = data["complaint"]

    print(f"Missing fields: {missing}")
    print(f"Complaint fields: {complaint}")

    # Batch number should be missing or null (not invented)
    batch = complaint.get("batch_lot_number")
    assert not batch or batch.lower() in ("not provided", "unknown", "n/a"), \
        f"Batch should not be invented: '{batch}'"

    # Missing fields should be reported
    assert len(missing) > 0, "Missing fields should be detected for incomplete complaint"
    print(f"[OK] Missing fields detection passed. Missing: {missing}")


# ─────────────────────────────────────────────
# Test 4: Follow-up batch number correction
# ─────────────────────────────────────────────

def test_followup_batch_number_correction():
    """User correction of batch number should only update that field."""
    # Current state (already extracted)
    current_complaint = {
        "product_name": "Amoxicillin Capsules",
        "batch_lot_number": "AMX240601",  # wrong batch
        "complaint_type": "Product Defect",
        "description": "Discolored capsules reported",
        "complaint_source": "Pharmacy",
        "customer_name": "ABC Pharmacy",
        "strength_grade": "500 mg",
        "quantity_affected": "12 capsules",
        "manufacturing_date": None,
        "expiry_date": None,
        "complaint_date": "September 10, 2026",
    }

    resp = client.post("/api/complaints/follow-up", json={
        "message": "Sorry, the batch number is actually BMX240602, not AMX240601.",
        "current_complaint": current_complaint,
    })

    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()

    updated = data["complaint"]
    print(f"Updated complaint: {data.get('updated_fields')}")

    assert updated.get("batch_lot_number") == "BMX240602", \
        f"Batch should be updated to BMX240602, got: {updated.get('batch_lot_number')}"
    # Other fields should be preserved
    assert updated.get("product_name") == "Amoxicillin Capsules", "Product name should not change"
    print(f"[OK] Batch correction passed. New batch: {updated.get('batch_lot_number')}")


# ─────────────────────────────────────────────
# Test 5: Follow-up quantity correction
# ─────────────────────────────────────────────

def test_followup_quantity_correction():
    """User correction of quantity should only update quantity_affected."""
    current_complaint = {
        "product_name": "Metformin Tablets",
        "batch_lot_number": "MET240901",
        "complaint_type": "Foreign Matter Contamination",
        "description": "Black particles found in tablets",
        "complaint_source": "Pharmacy",
        "customer_name": "City Hospital",
        "strength_grade": "500 mg",
        "quantity_affected": "2 tablets",  # wrong quantity
        "manufacturing_date": None,
        "expiry_date": None,
        "complaint_date": None,
    }

    resp = client.post("/api/complaints/follow-up", json={
        "message": "The quantity affected is 48 capsules, not 2.",
        "current_complaint": current_complaint,
    })

    assert resp.status_code == 200
    data = resp.json()
    updated = data["complaint"]

    print(f"Updated fields: {data.get('updated_fields')}")
    # Quantity should be updated
    qty = updated.get("quantity_affected", "")
    assert "48" in str(qty), f"Quantity should contain '48', got: '{qty}'"
    # Batch should be unchanged
    assert updated.get("batch_lot_number") == "MET240901", "Batch should not change"
    print(f"[OK] Quantity correction passed. New quantity: {qty}")


# ─────────────────────────────────────────────
# Test 6: Risk assessment is included in response
# ─────────────────────────────────────────────

CONTAMINATION_COMPLAINT = """
City Hospital Pharmacy found small black metallic particles in 3 tablets of
Metformin 500mg, batch MET240901. Manufacturing date July 2024, expiry July 2026.
Patient consumed 1 tablet before the contamination was noticed.
"""

def test_risk_assessment_present_and_valid():
    """Risk assessment should have valid severity and priority."""
    resp = client.post("/api/complaints/analyze-text", json={"text": CONTAMINATION_COMPLAINT})
    assert resp.status_code == 200
    data = resp.json()

    risk = data.get("risk", {})
    print(f"Risk: {risk}")

    assert risk.get("severity") in ("Minor", "Major", "Critical"), \
        f"Invalid severity: {risk.get('severity')}"
    assert risk.get("priority") in ("Low", "Medium", "High", "Critical"), \
        f"Invalid priority: {risk.get('priority')}"
    assert risk.get("rationale"), "Risk rationale should be present"
    assert risk.get("suggested_next_action"), "Suggested action should be present"

    print(f"[OK] Risk assessment passed. Severity: {risk['severity']}, Priority: {risk['priority']}")


# ─────────────────────────────────────────────
# Test 7: QMS commit
# ─────────────────────────────────────────────

def test_qms_commit():
    """Committed complaint should be persisted and return a complaint ID."""
    payload = {
        "complaint": {
            "complaint_source": "Pharmacy",
            "customer_name": "ABC Pharmacy",
            "product_name": "Amoxicillin Capsules",
            "strength_grade": "500 mg",
            "batch_lot_number": "AMX240602",
            "manufacturing_date": "January 2024",
            "expiry_date": "June 2027",
            "quantity_affected": "12 capsules",
            "complaint_type": "Product Defect",
            "complaint_date": "September 10, 2026",
            "description": "Customer reported 12 discolored capsules (yellowish-brown) from the above batch.",
        },
        "risk": {
            "category": "Product Defect",
            "severity": "Major",
            "priority": "High",
            "rationale": "Discoloration may indicate degradation or contamination affecting product quality.",
            "suggested_next_action": "Quarantine batch AMX240602. Conduct stability testing and visual inspection.",
        },
        "missing_fields": [],
        "confidence": {},
    }

    resp = client.post("/api/complaints/new/commit", json=payload)
    assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("complaint_id"), "Should return a complaint ID"
    assert data.get("status") == "committed"
    print(f"[OK] QMS commit passed. ID: {data['complaint_id']}")

    # Verify we can retrieve it
    complaint_id = data["complaint_id"]
    get_resp = client.get(f"/api/complaints/{complaint_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["batch_lot_number"] == "AMX240602"
    print(f"[OK] Committed complaint retrievable: {fetched['id']}")


# ─────────────────────────────────────────────
# Test 8: API validation errors
# ─────────────────────────────────────────────

def test_short_text_rejected():
    """Very short text should be rejected with 422."""
    resp = client.post("/api/complaints/analyze-text", json={"text": "hi"})
    assert resp.status_code == 422
    print("[OK] Short text validation passed")


def test_missing_text_field_rejected():
    """Missing text field should return 422."""
    resp = client.post("/api/complaints/analyze-text", json={})
    assert resp.status_code == 422
    print("[OK] Missing field validation passed")
