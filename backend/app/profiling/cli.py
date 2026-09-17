"""NVIDIA NeMo Agent Toolkit (nvidia-nat) CLI Profiling Runner.

Run multi-agent profiling benchmarks directly from the command line:
    python -m backend.app.profiling.cli profile --query "I have chest pain"
"""

import sys
import json
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from backend.app.agents.root_agent import root_supervisor
from backend.app.profiling.profiler import agent_profiler
from backend.app.profiling.nat_profiler_bridge import nat_profiler_bridge

console = Console(safe_box=True)


def run_profile_command(query: str, patient_id: int = 1, session_id: str = "cli_bench_1"):
    console.print(Panel(f"[bold cyan]NVIDIA NeMo Agent Toolkit Profiler[/bold cyan]\nTarget Query: [yellow]{query}[/yellow]", title="[NAT] HopeCare Profiler"))
    
    with console.status("[bold green]Executing agentic workflow with NAT trace hooks...[/bold green]"):
        result = root_supervisor.execute_workflow(
            message=query,
            context={"session_id": session_id, "patient_id": patient_id}
        )

    # Fetch recent trace
    recent_traces = agent_profiler.get_recent_traces(limit=1)
    if not recent_traces:
        console.print("[red]No trace recorded.[/red]")
        return

    trace = recent_traces[0]

    # 1. High Level Execution Metrics Table
    summary_table = Table(title="Execution & SLA Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Trace ID", str(trace["trace_id"]))
    summary_table.add_row("Route Selected", str(trace["route"]))
    summary_table.add_row("Delegated Agent", str(trace["delegated_agent"]))
    summary_table.add_row("Emergency Status", "EMERGENCY" if trace["is_emergency"] else "Standard")
    summary_table.add_row("Total Latency", f"{trace['total_latency_ms']:.2f} ms")
    summary_table.add_row("Routing Latency", f"{trace['routing_latency_ms']:.2f} ms")
    summary_table.add_row("Agent Latency", f"{trace['agent_latency_ms']:.2f} ms")
    summary_table.add_row("Tools Latency", f"{trace['tools_latency_ms']:.2f} ms")
    summary_table.add_row("Tools Invocations", ", ".join(trace["tools_called"]) or "None")
    summary_table.add_row("Tokens (Est.)", f"{trace['tokens']['total']} (Prompt: {trace['tokens']['prompt']}, Completion: {trace['tokens']['completion']})")
    console.print(summary_table)

    # 2. Step-by-Step Waterfall
    waterfall_table = Table(title="Step-by-Step Waterfall Timeline", show_header=True, header_style="bold blue")
    waterfall_table.add_column("Category", style="cyan")
    waterfall_table.add_column("Step Name", style="white")
    waterfall_table.add_column("Duration (ms)", justify="right", style="yellow")
    waterfall_table.add_column("Status", style="green")

    for ev in trace.get("events", []):
        waterfall_table.add_row(
            ev["category"],
            ev["name"],
            f"{ev['duration_ms']:.2f}",
            ev["status"]
        )
    console.print(waterfall_table)

    # 3. NVIDIA NAT Bottleneck Analysis
    bottlenecks = nat_profiler_bridge.get_bottleneck_analysis()
    console.print(Panel(
        f"[bold]Primary Bottleneck:[/bold] [red]{bottlenecks['primary_bottleneck'].upper()}[/red]\n"
        f"[bold]Total Measured Stack:[/bold] {bottlenecks['total_measured_latency_ms']:.2f} ms\n"
        + "\n".join([f" - {k.title()}: {v['total_ms']:.2f} ms ({v['percentage']}%)" for k, v in bottlenecks["breakdown"].items()]),
        title="NVIDIA NAT Bottleneck Analysis"
    ))

    # 4. NVIDIA NAT Prediction Trie
    trie_info = nat_profiler_bridge.get_trie_summary()
    trie_tree = Tree("[bold green]NVIDIA NAT Prediction Trie[/bold green]")
    trie_tree.add(f"Indexed Traces: {trie_info.get('total_traces_indexed', 0)}")
    trie_tree.add(f"Branch Children: {trie_info.get('total_children', 0)}")
    console.print(trie_tree)


    console.print("\n[bold green]Workflow Response:[/bold green]")
    console.print(result.get("response", ""))


def main():
    parser = argparse.ArgumentParser(description="HopeCare NVIDIA NeMo Agent Toolkit (NAT) Profiler CLI")
    subparsers = parser.add_subparsers(dest="command")

    profile_parser = subparsers.add_parser("profile", help="Run profiling benchmark on a patient query")
    profile_parser.add_argument("--query", "-q", type=str, required=True, help="Clinical or operational user query")
    profile_parser.add_argument("--patient-id", "-p", type=int, default=1, help="Patient ID for context")
    profile_parser.add_argument("--session-id", "-s", type=str, default="cli_bench_1", help="Session ID")

    args = parser.parse_args()

    if args.command == "profile":
        run_profile_command(query=args.query, patient_id=args.patient_id, session_id=args.session_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
