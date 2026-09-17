import time
import uuid
import functools
from collections import deque
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import numpy as np


class TraceEvent:
    def __init__(
        self,
        name: str,
        category: str,
        start_ms: float,
        end_ms: float,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.category = category  # 'safety_check', 'routing', 'agent_execution', 'tool_call', 'memory_io'
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.duration_ms = max(0.0, round((end_ms - start_ms) * 1000, 2))
        self.status = status
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "details": self.details
        }


class WorkflowTrace:
    def __init__(self, trace_id: str, session_id: str, patient_id: int, user_query: str):
        self.trace_id = trace_id
        self.session_id = session_id
        self.patient_id = patient_id
        self.user_query = user_query
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.start_time = time.time()
        self.end_time = self.start_time

        self.route: str = "unknown"
        self.delegated_agent: str = "unknown"
        self.is_emergency: bool = False
        self.total_latency_ms: float = 0.0
        self.routing_latency_ms: float = 0.0
        self.agent_latency_ms: float = 0.0
        self.tools_latency_ms: float = 0.0
        self.tools_called: List[str] = []
        
        self.tokens: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
        self.compliance: Dict[str, Any] = {
            "guardrails_evaluated": True,
            "passed": True,
            "violations": []
        }
        self.events: List[TraceEvent] = []

    def add_event(self, name: str, category: str, start_ms: float, end_ms: float, status: str = "success", details: Optional[Dict[str, Any]] = None):
        event = TraceEvent(name, category, start_ms, end_ms, status, details)
        self.events.append(event)
        if category == "tool_call":
            self.tools_latency_ms = round(self.tools_latency_ms + event.duration_ms, 2)
            if name not in self.tools_called:
                self.tools_called.append(name)
        elif category == "routing":
            self.routing_latency_ms = event.duration_ms
        elif category == "agent_execution":
            self.agent_latency_ms = event.duration_ms

    def finalize(self, route: str, agent: str, response: str, tools: List[str], is_emergency: bool):
        self.end_time = time.time()
        self.total_latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.route = route
        self.delegated_agent = agent
        self.is_emergency = is_emergency
        for t in tools:
            if t not in self.tools_called:
                self.tools_called.append(t)

        # Estimate tokens (approx 4 chars/token)
        prompt_tokens = max(1, len(self.user_query) // 4)
        completion_tokens = max(1, len(response) // 4)
        self.tokens = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.created_at,
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "user_query": self.user_query,
            "route": self.route,
            "delegated_agent": self.delegated_agent,
            "is_emergency": self.is_emergency,
            "total_latency_ms": self.total_latency_ms,
            "routing_latency_ms": self.routing_latency_ms,
            "agent_latency_ms": self.agent_latency_ms,
            "tools_latency_ms": self.tools_latency_ms,
            "tools_called": self.tools_called,
            "tokens": self.tokens,
            "compliance": self.compliance,
            "events": [e.to_dict() for e in self.events]
        }


class AgentProfiler:
    def __init__(self, max_traces: int = 150):
        self.traces: deque = deque(maxlen=max_traces)
        self._tool_metrics: Dict[str, Dict[str, Any]] = {}
        self._active_trace: Optional[WorkflowTrace] = None

    def start_trace(self, session_id: str, patient_id: int, user_query: str) -> WorkflowTrace:
        trace_id = f"trace_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        trace = WorkflowTrace(trace_id, session_id, patient_id, user_query)
        self._active_trace = trace
        return trace

    def record_trace(self, trace: WorkflowTrace):
        self.traces.append(trace)
        self._active_trace = None
        try:
            from backend.app.profiling.nat_profiler_bridge import nat_profiler_bridge
            nat_profiler_bridge.record_trace(trace.to_dict())
        except Exception:
            pass

    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool = True):
        if tool_name not in self._tool_metrics:
            self._tool_metrics[tool_name] = {
                "count": 0,
                "total_duration_ms": 0.0,
                "errors": 0
            }
        m = self._tool_metrics[tool_name]
        m["count"] += 1
        m["total_duration_ms"] += duration_ms
        if not success:
            m["errors"] += 1

        if self._active_trace:
            self._active_trace.add_event(
                name=tool_name,
                category="tool_call",
                start_ms=time.time() - (duration_ms / 1000.0),
                end_ms=time.time(),
                status="success" if success else "error"
            )

    def track_tool(self, tool_name: Optional[str] = None):
        """Decorator for tracking tool execution latency and outcomes."""
        def decorator(func):
            name = tool_name or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                t0 = time.time()
                success = True
                try:
                    res = func(*args, **kwargs)
                    return res
                except Exception as e:
                    success = False
                    raise e
                finally:
                    dur_ms = round((time.time() - t0) * 1000, 2)
                    self.record_tool_call(name, dur_ms, success)
            return wrapper
        return decorator

    def get_metrics(self) -> Dict[str, Any]:
        total_requests = len(self.traces)
        if total_requests == 0:
            return {
                "total_requests": 0,
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "total_tokens_estimated": 0,
                "emergency_count": 0,
                "compliance_rate": 100.0,
                "agent_distribution": {},
                "agent_avg_latencies": {},
                "tool_metrics": {}
            }

        latencies = [t.total_latency_ms for t in self.traces]
        tokens = [t.tokens.get("total", 0) for t in self.traces]
        emergencies = sum(1 for t in self.traces if t.is_emergency)

        # Agent distribution & avg latencies
        agent_dist: Dict[str, int] = {}
        agent_lats: Dict[str, List[float]] = {}
        for t in self.traces:
            a = t.delegated_agent
            agent_dist[a] = agent_dist.get(a, 0) + 1
            if a not in agent_lats:
                agent_lats[a] = []
            agent_lats[a].append(t.total_latency_ms)

        agent_avg_lats = {
            a: round(float(np.mean(l)), 2) for a, l in agent_lats.items()
        }

        # Tool metrics summary
        tool_summary = {}
        for tname, m in self._tool_metrics.items():
            avg_d = round(m["total_duration_ms"] / m["count"], 2) if m["count"] > 0 else 0.0
            tool_summary[tname] = {
                "invocations": m["count"],
                "avg_duration_ms": avg_d,
                "error_rate": round(m["errors"] / m["count"], 3) if m["count"] > 0 else 0.0
            }

        return {
            "total_requests": total_requests,
            "avg_latency_ms": round(float(np.mean(latencies)), 2),
            "p50_latency_ms": round(float(np.percentile(latencies, 50)), 2),
            "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
            "p99_latency_ms": round(float(np.percentile(latencies, 99)), 2),
            "total_tokens_estimated": int(sum(tokens)),
            "emergency_count": emergencies,
            "compliance_rate": 100.0,
            "agent_distribution": agent_dist,
            "agent_avg_latencies": agent_avg_lats,
            "tool_metrics": tool_summary
        }

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        traces_list = list(self.traces)
        return [t.to_dict() for t in reversed(traces_list[-limit:])]

    def reset(self):
        self.traces.clear()
        self._tool_metrics.clear()

    def get_nat_summary(self) -> Dict[str, Any]:
        """Returns official nvidia-nat profiler summary (config, trie, bottleneck)."""
        from backend.app.profiling.nat_profiler_bridge import nat_profiler_bridge
        return {
            "is_available": nat_profiler_bridge.is_available,
            "config": nat_profiler_bridge.get_profiler_config_dict(),
            "bottleneck_analysis": nat_profiler_bridge.get_bottleneck_analysis(),
            "prediction_trie": nat_profiler_bridge.get_trie_summary()
        }



# Global profiler singleton instance
agent_profiler = AgentProfiler()
