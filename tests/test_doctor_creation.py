import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_create_doctor_with_auto_generated_id():
    payload = {
        "name": "Dr. Marcus Vance",
        "department_name": "Cardiology"
    }
    response = client.post("/api/v1/doctors", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"] is not None
    assert data["name"] == "Dr. Marcus Vance"
    assert data["department"] == "Cardiology"
    assert data["license_number"].startswith("DOC-")

    # Verify doctor is present in directory listing
    list_resp = client.get(f"/api/v1/doctors?query=Vance")
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert any(d["id"] == data["id"] for d in docs)

    # Verify doctor has auto-generated schedules and slots for next Monday
    # (Monday is weekday 0, which is always in Mon-Fri schedule)
    import datetime
    today = datetime.date.today()
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    next_monday = today + datetime.timedelta(days=days_ahead)
    monday_str = next_monday.strftime("%Y-%m-%d")

    slot_resp = client.get(f"/api/v1/doctors/{data['id']}/slots?date={monday_str}")
    assert slot_resp.status_code == 200
    slots_data = slot_resp.json()
    assert len(slots_data["slots"]) > 0
    assert "09:00" in slots_data["slots"]
