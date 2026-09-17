import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.profiles.loader import profile_registry
from backend.app.profiling.nat_profiler_bridge import nat_profiler_bridge
from backend.app.profiling.profiler import agent_profiler

client = TestClient(app)


def test_nat_package_imports():
    """Verify that official nvidia-nat package and core components import successfully."""
    import nat
    from nat.data_models.agent import AgentBaseConfig
    from nat.data_models.profiler import ProfilerConfig, BottleneckConfig, PredictionTrieConfig
    from nat.profiler.prediction_trie.trie_builder import PredictionTrieBuilder
    from nat.data_models.intermediate_step import IntermediateStep, IntermediateStepType

    assert hasattr(nat, "__file__")
    assert AgentBaseConfig is not None
    assert ProfilerConfig is not None
    assert PredictionTrieBuilder is not None


def test_nat_agent_base_configs_generation():
    """Verify that all 7 hospital sub-agent profiles generate valid official AgentBaseConfig instances."""
    configs = profile_registry.get_nat_agent_configs()
    assert len(configs) >= 7
    expected_agents = [
        "root_supervisor", "emergency_agent", "doctor_agent",
        "appointment_agent", "patient_agent", "hospital_agent", "medical_agent"
    ]
    for agent_name in expected_agents:
        assert agent_name in configs
        cfg = configs[agent_name]
        assert cfg.name == agent_name
        assert cfg.llm_name == "gemini-2.5-flash"
        assert len(cfg.description) > 5


def test_nat_workflow_config_validation():
    """Verify that nat_workflow.yaml loads cleanly according to official NAT runtime schemas."""
    from nat.runtime.loader import load_config
    cfg = load_config("nat_workflow.yaml")
    assert cfg is not None
    assert cfg.workflow.type == "chat_completion"
    assert cfg.general.enable_per_user_monitoring is True
    assert cfg.eval.general.profiler is not None
    assert cfg.eval.general.profiler.bottleneck_analysis.enable_simple_stack is True


def test_nat_profiler_bridge_and_trie():
    """Verify that NATProfilerBridge records traces and updates prediction trie and bottlenecks."""
    mock_trace = {
        "trace_id": "test_nat_trace_1",
        "user_query": "Find doctor",
        "route": "doctor",
        "delegated_agent": "Doctor Agent",
        "is_emergency": False,
        "total_latency_ms": 150.0,
        "events": [
            {"step_type": "safety_check", "name": "detect_emergency", "duration_ms": 2.0, "status": "success"},
            {"step_type": "routing", "name": "classify_intent", "duration_ms": 15.0, "status": "success"},
            {"step_type": "agent_execution", "name": "doctor_agent.run", "duration_ms": 100.0, "status": "success"},
            {"step_type": "tool_call", "name": "search_doctors_tool", "duration_ms": 33.0, "status": "success"},
        ]
    }
    nat_profiler_bridge.record_trace(mock_trace)

    trie_info = nat_profiler_bridge.get_trie_summary()
    assert trie_info.get("enabled") is True
    assert trie_info.get("total_traces_indexed", 0) >= 1

    bottlenecks = nat_profiler_bridge.get_bottleneck_analysis()
    assert bottlenecks["total_measured_latency_ms"] > 0
    assert "breakdown" in bottlenecks
    assert "agent_execution" in bottlenecks["breakdown"]


def test_api_nat_summary_and_benchmark():
    """Verify REST API endpoints for NAT summary and live benchmarking."""
    resp_sum = client.get("/api/v1/profiler/nat/summary")
    assert resp_sum.status_code == 200
    data_sum = resp_sum.json()
    assert data_sum["is_available"] is True
    assert "config" in data_sum
    assert "bottleneck_analysis" in data_sum
    assert "prediction_trie" in data_sum

    resp_bench = client.post("/api/v1/profiler/nat/benchmark", json={
        "query": "Is there an emergency cardiac doctor?",
        "patient_id": 1
    })
    assert resp_bench.status_code == 200
    data_bench = resp_bench.json()
    assert data_bench["status"] == "success"
    assert "trace" in data_bench
    assert "response" in data_bench
