from __future__ import annotations

import json
from pathlib import Path

import dspy

from db.base import SessionLocal
from db.crud import create_candidate, get_experiment, set_experiment_status
from db.models import PromptStatus
from db.schemas import CandidateCreate
from optimizer.dataset import build_v2_splits
from optimizer.evaluation import ModuleEvaluation, evaluate_module
from orchestration.graph import build_optimization_graph
from src.optimization.provider import resolve_model_provider


def _candidate_payload(
    prompt_text: str,
    generation: int,
    evaluation: ModuleEvaluation,
    *,
    parent_id: str | None = None,
) -> CandidateCreate:
    fitness = (
        0.35 * evaluation.pass_rate
        + 0.35 * evaluation.mutation_score
        + 0.20 * evaluation.branch_coverage
        + 0.10 * evaluation.statement_coverage
    )
    return CandidateCreate(
        parent_id=parent_id,
        generation=generation,
        prompt_text=prompt_text,
        fitness_score=fitness,
        pass_rate=evaluation.pass_rate,
        statement_coverage=evaluation.statement_coverage,
        branch_coverage=evaluation.branch_coverage,
        mutation_score=evaluation.mutation_score,
        latency_seconds=evaluation.latency_seconds,
    )


def execute_experiment(experiment_id: str) -> None:
    """Background worker entry point used by the v3 API."""
    session = SessionLocal()
    try:
        experiment = get_experiment(session, experiment_id)
        if experiment is None:
            return
        set_experiment_status(session, experiment, PromptStatus.OPTIMIZED)
        train, validation, _holdout = build_v2_splits(
            experiment.dataset_path,
            experiment.source_root,
            harness_module_path=experiment.module_path,
        )
        provider = resolve_model_provider()
        lm = dspy.LM(provider.optimization_model)
        dspy.configure(lm=lm)
        state = build_optimization_graph().invoke(
            {
                "experiment_id": experiment.id,
                "module_path": experiment.module_path,
                "trainset": train,
                "valset": validation,
                "budget_limit_usd": experiment.budget_limit,
                "reflection_lm": lm,
                "baseline_prompt": experiment.baseline_prompt,
                "gepa_log_dir": str(Path("eval") / "dspy_gepa" / experiment.id),
            }
        )
        baseline_evaluation = evaluate_module(state["baseline_module"], validation)
        optimized_evaluation = evaluate_module(state["optimized_module"], validation)
        baseline = create_candidate(
            session,
            experiment.id,
            _candidate_payload(experiment.baseline_prompt, 0, baseline_evaluation),
        )
        optimized_state = state["optimized_module"].dump_state()
        create_candidate(
            session,
            experiment.id,
            _candidate_payload(
                json.dumps(optimized_state, ensure_ascii=False, default=str),
                1,
                optimized_evaluation,
                parent_id=baseline.id,
            ),
        )
        set_experiment_status(session, experiment, PromptStatus.IN_REVIEW)
    except Exception as exc:
        experiment = get_experiment(session, experiment_id)
        if experiment is not None:
            set_experiment_status(
                session,
                experiment,
                PromptStatus.FAILED,
                error_message=str(exc)[-4000:],
            )
    finally:
        session.close()
