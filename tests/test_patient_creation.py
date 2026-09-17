import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_create_patient_with_auto_generated_id():
    payload = {
        "name": "Emma Watson",
        "gender": "Female",
        "date_of_birth": "1990-04-15",
        "blood_group": "A+",
        "phone_number": "+1-555-0188"
    }
    response = client.post("/api/v1/patients", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"] is not None
    assert data["name"] == "Emma Watson"
    assert data["gender"] == "Female"
    assert data["blood_group"] == "A+"
    assert data["policy"].startswith("HC-POL-")

    # Verify patient is in list_patients
    list_resp = client.get("/api/v1/patients")
    assert list_resp.status_code == 200
    pts = list_resp.json()
    assert any(p["id"] == data["id"] for p in pts)

    # Verify patient profile
    prof_resp = client.get(f"/api/v1/patients/{data['id']}")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()
    assert prof["full_name"] == "Emma Watson"
    assert prof["blood_group"] == "A+"
