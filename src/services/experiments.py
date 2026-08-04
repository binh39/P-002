from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import dspy

from db.base import SessionLocal
from db.crud import create_candidate, get_experiment, set_experiment_status
from db.models import PromptStatus
from db.schemas import CandidateCreate
from src.optimization.dataset import load_targets
from src.optimization.gepa import evaluate_bundle_repeated, optimize
from src.optimization.models import ExperimentConfig
from src.optimization.prompts import PromptBundle
from src.optimization.provider import resolve_model_provider
from src.optimization.runner import CoverUpExperimentRunner

DEFAULT_BASELINE_PROMPT = Path(
    "eval/prompt_optimization/prompts/gpt_v2_baseline.json"
)
GEPA_MAX_METRIC_CALLS = 300


def _project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = (path if path.is_absolute() else project_root / path).resolve()
    if not resolved.is_relative_to(project_root):
        raise ValueError(f"Experiment path must stay inside the project: {value}")
    return resolved


def _valid_target_rate(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    valid = sum(
        1
        for result in results
        if result.get("coverage") is not None
        and result["coverage"].get("valid") is not False
    )
    return valid / len(results)


def _strategy_payload(
    strategy: str,
    bundle: PromptBundle,
    generation: int,
    evaluation: dict[str, Any],
    *,
    latency_seconds: float = 0.0,
    parent_id: str | None = None,
) -> CandidateCreate:
    aggregate = evaluation["aggregate"]
    return CandidateCreate(
        parent_id=parent_id,
        generation=generation,
        prompt_text=json.dumps(
            {"strategy": strategy, "prompt_bundle": bundle.as_candidate()},
            indent=2,
            ensure_ascii=False,
        ),
        fitness_score=float(aggregate["score"]),
        pass_rate=_valid_target_rate(evaluation["results"]),
        statement_coverage=float(aggregate["statement_coverage"]),
        branch_coverage=float(aggregate["branch_coverage"]),
        cost_usd=0.0,
        latency_seconds=latency_seconds,
    )


def execute_experiment(experiment_id: str) -> None:
    """Compare the fixed CoverUp prompt bundle with its GEPA-optimized bundle."""
    session = SessionLocal()
    try:
        experiment = get_experiment(session, experiment_id)
        if experiment is None:
            return
        set_experiment_status(session, experiment, PromptStatus.OPTIMIZED)

        project_root = Path.cwd().resolve()
        baseline_path = _project_path(project_root, experiment.baseline_prompt)
        expected_baseline = (project_root / DEFAULT_BASELINE_PROMPT).resolve()
        if baseline_path != expected_baseline:
            raise ValueError(
                "The UI experiment baseline must be "
                f"{DEFAULT_BASELINE_PROMPT.as_posix()}"
            )
        baseline = PromptBundle.load(baseline_path)

        dataset_path = _project_path(project_root, experiment.dataset_path)
        package_dir = _project_path(project_root, experiment.module_path)
        source_root = _project_path(project_root, experiment.source_root)
        tests_dir = source_root / "tests"
        for label, path in (
            ("baseline prompt", baseline_path),
            ("dataset", dataset_path),
            ("package", package_dir),
            ("tests", tests_dir),
        ):
            if not path.exists():
                raise FileNotFoundError(f"The {label} path does not exist: {path}")

        artifacts = project_root / "eval" / "dspy_gepa" / experiment.id
        runner = CoverUpExperimentRunner(
            ExperimentConfig(
                project_root=project_root,
                package_dir=package_dir,
                tests_dir=tests_dir,
                artifacts_dir=artifacts,
                workspace_root=project_root / ".pytest_tmp" / experiment.id,
                coverup_model=resolve_model_provider().generation_model,
                max_attempts=3,
                repeat_tests=2,
                max_concurrency=10,
            )
        )
        train = load_targets(dataset_path, "train")
        validation = load_targets(dataset_path, "validation")
        if not train or not validation:
            raise ValueError("GEPA requires non-empty train and validation splits")

        provider = resolve_model_provider()
        reflection_lm = dspy.LM(
            provider.optimization_model,
            max_tokens=8192,
            temperature=0.7,
        )
        started = time.monotonic()
        optimized = optimize(
            runner=runner,
            train_targets=train,
            validation_targets=validation,
            baseline=baseline,
            reflection_lm=reflection_lm,
            artifacts_dir=artifacts,
            auto=None,
            max_metric_calls=GEPA_MAX_METRIC_CALLS,
        )
        optimization_latency = time.monotonic() - started

        optimized_path = artifacts / "prompts" / "gepa_optimized.json"
        optimized.best_bundle.save(optimized_path)
        baseline_evaluation = evaluate_bundle_repeated(
            runner,
            validation,
            baseline,
            artifacts / "candidates",
            split="validation",
            workspace_kind="baseline",
        )
        optimized_evaluation = evaluate_bundle_repeated(
            runner,
            validation,
            optimized.best_bundle,
            artifacts / "candidates",
            split="validation",
            workspace_kind="candidate",
            reference_results=baseline_evaluation["results"],
        )

        coverup = create_candidate(
            session,
            experiment.id,
            _strategy_payload("coverup", baseline, 0, baseline_evaluation),
        )
        create_candidate(
            session,
            experiment.id,
            _strategy_payload(
                "gepa",
                optimized.best_bundle,
                1,
                optimized_evaluation,
                latency_seconds=optimization_latency,
                parent_id=coverup.id,
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
