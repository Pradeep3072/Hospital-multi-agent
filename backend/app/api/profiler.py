from fastapi import APIRouter, Query
from backend.app.profiling.profiler import agent_profiler

router = APIRouter(prefix="/profiler", tags=["NeMo Agent Profiler"])


@router.get("/metrics")
def get_profiler_metrics():
    """
    Retrieve real-time multi-agent execution telemetry, latency percentiles, and tool metrics.
    """
    return agent_profiler.get_metrics()


@router.get("/traces")
def get_recent_traces(limit: int = Query(20, ge=1, le=100)):
    """
    Retrieve recent execution traces with waterfall step breakdowns.
    """
    traces = agent_profiler.get_recent_traces(limit=limit)
    return {
        "count": len(traces),
        "traces": traces
    }


@router.post("/reset")
def reset_profiler_metrics():
    """
    Reset all collected profiling traces and tool metrics.
    """
    agent_profiler.reset()
    return {"status": "success", "message": "NeMo agent telemetry metrics reset successfully."}


@router.get("/nat/summary")
def get_nat_profiler_summary():
    """
    Retrieve official nvidia-nat profiler configuration, prediction trie, and bottleneck analysis.
    """
    from backend.app.profiling.nat_profiler_bridge import nat_profiler_bridge
    return {
        "is_available": nat_profiler_bridge.is_available,
        "config": nat_profiler_bridge.get_profiler_config_dict(),
        "bottleneck_analysis": nat_profiler_bridge.get_bottleneck_analysis(),
        "prediction_trie": nat_profiler_bridge.get_trie_summary()
    }


@router.post("/nat/benchmark")
def run_nat_benchmark(payload: dict):
    """
    Run on-demand multi-agent benchmark with live NAT tracing and bottleneck analysis.
    """
    from backend.app.agents.root_agent import root_supervisor
    from backend.app.profiling.nat_profiler_bridge import nat_profiler_bridge

    query = payload.get("query", "What are the cardiology department hours?")
    patient_id = payload.get("patient_id", 1)
    session_id = payload.get("session_id", "bench_live_session")

    result = root_supervisor.execute_workflow(
        message=query,
        context={"session_id": session_id, "patient_id": patient_id}
    )

    recent_traces = agent_profiler.get_recent_traces(limit=1)
    trace = recent_traces[0] if recent_traces else None

    return {
        "status": "success",
        "query": query,
        "trace": trace,
        "bottleneck_analysis": nat_profiler_bridge.get_bottleneck_analysis(),
        "trie_summary": nat_profiler_bridge.get_trie_summary(),
        "response": result.get("response", "")
    }

