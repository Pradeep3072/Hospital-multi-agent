"""NVIDIA NeMo Agent Toolkit (nvidia-nat) Profiler Bridge.

Connects HopeCare's multi-agent workflows directly to official NVIDIA NAT data
models:
  - nat.data_models.profiler.ProfilerConfig
  - nat.data_models.intermediate_step.IntermediateStep & IntermediateStepType
  - nat.profiler.prediction_trie.trie_builder.PredictionTrieBuilder
  - nat.data_models.invocation_node.InvocationNode
"""

import time
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    from nat.data_models.profiler import (
        ProfilerConfig,
        BottleneckConfig,
        PredictionTrieConfig,
        ConcurrencySpikeConfig,
    )
    from nat.data_models.intermediate_step import (
        IntermediateStep,
        IntermediateStepPayload,
        IntermediateStepType,
    )
    from nat.data_models.invocation_node import InvocationNode
    from nat.profiler.prediction_trie.trie_builder import PredictionTrieBuilder
    from nat.profiler.prediction_trie.serialization import _serialize_node
    NAT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"nvidia-nat package not fully available: {e}")
    NAT_AVAILABLE = False
    ProfilerConfig = None
    PredictionTrieBuilder = None


class NATProfilerBridge:
    """Bridges HopeCare multi-agent workflow traces into official NVIDIA NAT profiler structures."""

    def __init__(self):
        self.is_available = NAT_AVAILABLE
        if self.is_available and ProfilerConfig:
            self.config = ProfilerConfig(
                base_metrics=True,
                token_usage_forecast=True,
                workflow_runtime_forecast=True,
                compute_llm_metrics=True,
                bottleneck_analysis=BottleneckConfig(
                    enable_simple_stack=True,
                    enable_nested_stack=True
                ),
                concurrency_spike_analysis=ConcurrencySpikeConfig(
                    enable=True,
                    spike_threshold=2
                ),
                prediction_trie=PredictionTrieConfig(
                    enable=True,
                    output_filename="prediction_trie.json"
                ),
            )
            self.trie_builder = PredictionTrieBuilder()
        else:
            self.config = None
            self.trie_builder = None

        self._trace_count = 0
        self._category_durations = {
            "safety_check": 0.0,
            "routing": 0.0,
            "agent_execution": 0.0,
            "tool_call": 0.0,
            "memory_io": 0.0
        }
        self._step_type_counts = {
            "FUNCTION": 0,
            "TOOL": 0,
            "TASK": 0,
            "CUSTOM": 0
        }

    def convert_trace_to_nat_steps(self, trace_dict: Dict[str, Any]) -> List[Any]:
        """Converts a HopeCare trace dictionary to a list of official NAT IntermediateStep items."""
        if not self.is_available:
            return []

        steps = []
        workflow_id = trace_dict.get("trace_id", "wf_0")
        root_node = InvocationNode(
            function_id=workflow_id,
            function_name="root_supervisor",
            parent_id="root",
            parent_name=""
        )

        base_time = trace_dict.get("start_time", time.time())
        current_offset = 0.0

        for idx, event in enumerate(trace_dict.get("events", [])):
            ev_type_str = event.get("step_type", "agent_execution")
            ev_name = event.get("name", f"step_{idx}")
            duration_sec = event.get("duration_ms", 1.0) / 1000.0

            # Map to NAT IntermediateStepType
            if ev_type_str == "routing":
                start_type = IntermediateStepType.TASK_START
                end_type = IntermediateStepType.TASK_END
                self._step_type_counts["TASK"] += 1
            elif ev_type_str == "tool_call":
                start_type = IntermediateStepType.TOOL_START
                end_type = IntermediateStepType.TOOL_END
                self._step_type_counts["TOOL"] += 1
            elif ev_type_str == "safety_check":
                start_type = IntermediateStepType.CUSTOM_START
                end_type = IntermediateStepType.CUSTOM_END
                self._step_type_counts["CUSTOM"] += 1
            else:
                start_type = IntermediateStepType.FUNCTION_START
                end_type = IntermediateStepType.FUNCTION_END
                self._step_type_counts["FUNCTION"] += 1

            # Accumulate category latency
            if ev_type_str in self._category_durations:
                self._category_durations[ev_type_str] += event.get("duration_ms", 0.0)

            node = InvocationNode(
                function_id=f"{workflow_id}_{idx}",
                function_name=ev_name,
                parent_id=workflow_id,
                parent_name="root_supervisor"
            )

            p_start = IntermediateStepPayload(
                event_type=start_type,
                event_timestamp=base_time + current_offset,
                name=ev_name,
                metadata=event.get("metadata", {})
            )
            step_start = IntermediateStep(
                parent_id=workflow_id,
                function_ancestry=node,
                payload=p_start
            )
            steps.append(step_start)

            current_offset += duration_sec

            p_end = IntermediateStepPayload(
                event_type=end_type,
                event_timestamp=base_time + current_offset,
                name=ev_name,
                metadata=event.get("metadata", {})
            )
            step_end = IntermediateStep(
                parent_id=workflow_id,
                function_ancestry=node,
                payload=p_end
            )
            steps.append(step_end)

        return steps

    def record_trace(self, trace_dict: Dict[str, Any]) -> None:
        """Records a completed trace into the official NVIDIA NAT prediction trie."""
        if not self.is_available or not self.trie_builder:
            return

        try:
            steps = self.convert_trace_to_nat_steps(trace_dict)
            if steps:
                self.trie_builder.add_trace(steps)
                self._trace_count += 1
        except Exception as e:
            logger.warning(f"Failed to record trace into NAT PredictionTrie: {e}")

    def get_trie_summary(self) -> Dict[str, Any]:
        """Builds and serializes the active NVIDIA NAT Prediction Trie."""
        if not self.is_available or not self.trie_builder:
            return {
                "enabled": False,
                "reason": "nvidia-nat not installed or initialized"
            }

        try:
            node = self.trie_builder.build()
            serialized = _serialize_node(node)
            return {
                "enabled": True,
                "total_traces_indexed": self._trace_count,
                "root": serialized,
                "total_children": len(serialized.get("children", {}))
            }
        except Exception as e:
            return {
                "enabled": True,
                "error": str(e),
                "total_traces_indexed": self._trace_count
            }

    def get_bottleneck_analysis(self) -> Dict[str, Any]:
        """Calculates latency stack breakdown across categories."""
        total_ms = sum(self._category_durations.values())
        breakdown = {}
        for cat, dur in self._category_durations.items():
            pct = round((dur / total_ms * 100), 1) if total_ms > 0 else 0.0
            breakdown[cat] = {
                "total_ms": round(dur, 2),
                "percentage": pct
            }

        # Identify primary bottleneck
        primary_bottleneck = "None"
        if total_ms > 0:
            primary_bottleneck = max(self._category_durations, key=self._category_durations.get)

        return {
            "total_measured_latency_ms": round(total_ms, 2),
            "primary_bottleneck": primary_bottleneck,
            "breakdown": breakdown,
            "step_type_distribution": self._step_type_counts
        }

    def get_profiler_config_dict(self) -> Dict[str, Any]:
        """Returns the active NVIDIA NAT ProfilerConfig dictionary."""
        if self.config:
            return self.config.model_dump()
        return {}


# Global singleton bridge instance
nat_profiler_bridge = NATProfilerBridge()
