import pytest
from backend.app.agents.root_agent import root_supervisor
from backend.app.security.safety import detect_emergency


def test_detect_emergency_critical_symptoms():
    critical_messages = [
        "I am having crushing chest pain and shortness of breath",
        "Patient cannot breathe and has face drooping",
        "Severe hemorrhage and heavy bleeding from trauma",
        "Someone passed out and is unconscious"
    ]
    for msg in critical_messages:
        is_emerg, data = detect_emergency(msg)
        assert is_emerg is True
        assert data["triggered"] is True
        assert "LEVEL_1_TRAUMA_ESCALATION" in data["protocol"]


def test_detect_emergency_non_critical():
    normal_messages = [
        "What are the visiting hours for the hospital?",
        "Can I see a cardiologist tomorrow?",
        "How much does an MRI scan cost?",
        "Show me my current prescriptions"
    ]
    for msg in normal_messages:
        is_emerg, data = detect_emergency(msg)
        assert is_emerg is False


def test_root_agent_emergency_short_circuit():
    result = root_supervisor.execute_workflow(
        "Help! I have severe chest pain and cannot breathe",
        context={"patient_id": 1}
    )
    assert result["is_emergency"] is True
    assert result["delegated_agent"] == "Emergency Agent"
    assert "EMERGENCY PROTOCOL ACTIVATED" in result["response"]
