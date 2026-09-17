import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.profiles.loader import profile_registry
from backend.app.profiling.profiler import agent_profiler

client = TestClient(app)


def test_nemo_profiles_registry():
    profiles = profile_registry.list_profiles()
    assert len(profiles) == 7
    
    names = [p.name for p in profiles]
    assert "root_supervisor" in names
    assert "emergency_agent" in names
    assert "doctor_agent" in names
    assert "appointment_agent" in names
    assert "patient_agent" in names
    assert "hospital_agent" in names
    assert "medical_agent" in names

    # Check emergency agent SLA and priority
    emerg_p = profile_registry.get_profile("emergency_agent")
    assert emerg_p is not None
    assert emerg_p.metadata.get("clinical_priority") == "CRITICAL"
    assert len(emerg_p.behavioral_contract.principles) > 0


def test_ethos_contract_loaded():
    ethos = profile_registry.get_ethos()
    assert "HopeCare Clinical AI Ethos" in ethos
    assert "Non-Maleficence" in ethos
    assert "Emergency Precedence" in ethos


def test_profiler_tracing():
    agent_profiler.reset()
    trace = agent_profiler.start_trace(session_id="test_sess", patient_id=1, user_query="What doctors treat heart conditions?")
    
    trace.add_event("routing", "routing", 0.0, 0.05, details={"route": "doctor"})
    trace.add_event("doctor_agent.process", "agent_execution", 0.05, 0.15)
    trace.finalize("doctor", "Doctor Agent", "Dr. Marcus Vance is available in Cardiology.", ["get_doctors_by_specialty"], is_emergency=False)
    agent_profiler.record_trace(trace)

    metrics = agent_profiler.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["avg_latency_ms"] >= 0
    assert "Doctor Agent" in metrics["agent_distribution"]
    assert metrics["total_tokens_estimated"] > 0


def test_api_profiles_endpoints():
    res = client.get("/api/v1/profiles")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 7
    assert len(data["profiles"]) == 7

    # Single profile endpoint
    res_single = client.get("/api/v1/profiles/doctor_agent")
    assert res_single.status_code == 200
    doc_data = res_single.json()
    assert doc_data["name"] == "doctor_agent"
    assert "get_doctors_by_specialty" in doc_data["allowed_tools"]
    assert doc_data["raw_yaml"] is not None

    # Ethos endpoint
    res_ethos = client.get("/api/v1/profiles/ethos")
    assert res_ethos.status_code == 200
    assert "Non-Maleficence" in res_ethos.json()["content"]


def test_api_profiler_endpoints():
    res_metrics = client.get("/api/v1/profiler/metrics")
    assert res_metrics.status_code == 200
    m = res_metrics.json()
    assert "avg_latency_ms" in m
    assert "compliance_rate" in m

    res_traces = client.get("/api/v1/profiler/traces?limit=10")
    assert res_traces.status_code == 200
    t = res_traces.json()
    assert "traces" in t
