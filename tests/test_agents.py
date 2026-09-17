from google.adk import Agent, Runner
from backend.app.agents.root_agent import root_supervisor, adk_root_agent, adk_runner
from backend.app.agents.emergency_agent import emergency_agent
from backend.app.agents.appointment_agent import appointment_agent
from backend.app.agents.doctor_agent import doctor_agent
from backend.app.agents.patient_agent import patient_agent
from backend.app.agents.hospital_agent import hospital_agent
from backend.app.agents.medical_agent import medical_agent


def test_google_adk_agent_hierarchy():
    """Verify Google ADK Agent instances and sub-agent hierarchy."""
    assert isinstance(adk_root_agent, Agent)
    assert adk_root_agent.name == "root_supervisor"
    
    sub_agent_names = [a.name for a in adk_root_agent.sub_agents]
    assert "emergency_agent" in sub_agent_names
    assert "appointment_agent" in sub_agent_names
    assert "doctor_agent" in sub_agent_names
    assert "patient_agent" in sub_agent_names
    assert "hospital_agent" in sub_agent_names
    assert "medical_agent" in sub_agent_names


def test_google_adk_runner_setup():
    """Verify Google ADK Runner instance."""
    assert isinstance(adk_runner, Runner)
    assert adk_runner.agent.name == "root_supervisor"


def test_google_adk_tools_registered():
    """Verify that Google ADK Agent tools are properly attached."""
    assert len(emergency_agent.tools) >= 1
    assert len(appointment_agent.tools) >= 3
    assert len(doctor_agent.tools) >= 3
    assert len(patient_agent.tools) >= 3
    assert len(hospital_agent.tools) >= 3
    assert len(medical_agent.tools) >= 1


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


def test_routing_appointment_agent():
    res = root_supervisor.execute_workflow("I want to book an appointment with Dr. Mitchell", {"patient_id": 1})
    assert res["delegated_agent"] == "Appointment Agent"
    assert "slot" in res["response"].lower() or "mitchell" in res["response"].lower() or "appointment" in res["response"].lower()


def test_appointment_agent_does_not_autobook_on_generic_request():
    """Verify that a generic booking request never auto-confirms or auto-books an appointment without details."""
    res = root_supervisor.execute_workflow("can you book an appointment for tomorrow", {"patient_id": 1, "session_id": "test_no_autobook"})
    assert res["delegated_agent"] == "Appointment Agent"
    assert "book_appointment" not in res["tools_called"]
    assert "book_appointment_tool" not in res["tools_called"]
    # Must prompt for doctor or medical specialty
    resp_lower = res["response"].lower()
    assert "doctor" in resp_lower or "special" in resp_lower or "which" in resp_lower

