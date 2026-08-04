from __future__ import annotations

from optimizer.gepa import compile_gepa
from optimizer.module import TestGenReactModule

from .observability import experiment_span
from .state import OptimizationState


def init_baseline_node(state: OptimizationState) -> dict:
    return {
        "baseline_module": TestGenReactModule(
            module_path=state["module_path"],
            instructions=state.get("baseline_prompt"),
        )
    }


def run_gepa_node(state: OptimizationState) -> dict:
    with experiment_span(
        f"experiment-{state['experiment_id']}",
        {"train_size": len(state["trainset"]), "val_size": len(state["valset"])},
    ):
        optimized = compile_gepa(
            state["baseline_module"],
            state["trainset"],
            state["valset"],
            reflection_lm=state["reflection_lm"],
            auto="light",
            log_dir=state.get("gepa_log_dir"),
        )
    return {"optimized_module": optimized}


def persist_results_node(state: OptimizationState) -> dict:
    """Persistence hook; v3 replaces this marker with database candidate rows."""
    return {"optimized_module": state["optimized_module"]}
