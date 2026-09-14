from backend.app.agents.root_agent import root_supervisor


def test_routing_hospital_agent():
    res = root_supervisor.execute_workflow("What time does the hospital cafeteria open?", {"patient_id": 1})
    assert res["delegated_agent"] == "Hospital Agent"
    assert "cafeteria" in res["response"].lower() or "garden cafe" in res["response"].lower() or "6:30" in res["response"]


def test_routing_doctor_agent():
    res = root_supervisor.execute_workflow("Find an orthopedic surgeon", {"patient_id": 1})
    assert res["delegated_agent"] == "Doctor Agent"
    assert "Wilson" in res["response"] or "Orthopedic" in res["response"]


def test_routing_patient_agent():
    res = root_supervisor.execute_workflow("What are my active prescriptions?", {"patient_id": 1})
    assert res["delegated_agent"] == "Patient Agent"
    assert "Lisinopril" in res["response"]
