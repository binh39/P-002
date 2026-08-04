from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import init_baseline_node, persist_results_node, run_gepa_node
from .state import OptimizationState


def build_optimization_graph():
    graph = StateGraph(OptimizationState)
    graph.add_node("init_baseline", init_baseline_node)
    graph.add_node("run_gepa", run_gepa_node)
    graph.add_node("persist_results", persist_results_node)
    graph.set_entry_point("init_baseline")
    graph.add_edge("init_baseline", "run_gepa")
    graph.add_edge("run_gepa", "persist_results")
    graph.add_edge("persist_results", END)
    return graph.compile()
