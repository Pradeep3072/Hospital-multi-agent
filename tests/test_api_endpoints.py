from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_doctors_endpoint():
    response = client.get("/api/v1/doctors")
    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) > 0
    assert any("Sarah Mitchell" in d["name"] for d in doctors)


def test_patients_endpoint():
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) >= 3


def test_hospital_services_endpoint():
    response = client.get("/api/v1/hospital/services")
    assert response.status_code == 200
    services = response.json()
    assert len(services) > 0


def test_chat_api_endpoint():
    payload = {
        "message": "What are the visiting hours for general wards?",
        "patient_id": 1,
        "session_id": "test-session"
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["delegated_agent"] == "Hospital Agent"
    assert data["is_emergency"] is False
    assert len(data["response"]) > 0
