from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import dspy
from dotenv import load_dotenv

from .dataset import load_targets
from .gepa import (
    bundle_digest,
    evaluate_bundle_repeated,
    optimize,
    validate_bundle,
    validate_reference_evaluation,
)
from .metrics import aggregate_coverage_score
from .models import ExperimentConfig
from .prompts import PromptBundle, baseline_bundle
from .provider import resolve_model_provider
from .runner import CoverUpExperimentRunner


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Optimize CoverUp prompts with coverage.py and GEPA")
    result.add_argument("--project-root", type=Path, default=Path.cwd())
    result.add_argument("--package-dir", type=Path, default=Path("src/sample_repo/isort/isort"))
    result.add_argument("--tests-dir", type=Path, default=Path("src/sample_repo/isort/tests"))
    result.add_argument(
        "--baseline-tests-dir",
        type=Path,
        help=(
            "Score an existing baseline suite as an additional reference; prompt "
            "promotion still uses paired generated evaluations"
        ),
    )
    result.add_argument("--artifacts-dir", type=Path, default=Path("eval/prompt_optimization"))
    result.add_argument("--max-attempts", type=int, default=3)
    result.add_argument(
        "--repeat-tests", type=int, default=2,
        help="Repeat generated tests to reject flaky suites (default: 2)",
    )
    result.add_argument(
        "--max-concurrency", type=int, default=10,
        help="Maximum concurrent CoverUp model requests (default: 10)",
    )
    result.add_argument(
        "--rate-limit", type=int,
        help="Optional CoverUp token-per-minute limit",
    )
    result.add_argument("--pytest-args", default="")
    commands = result.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Create baseline prompt and sample dataset")
    init.add_argument("--force", action="store_true")

    evaluate = commands.add_parser("evaluate", help="Evaluate one prompt over a dataset split")
    evaluate.add_argument("--dataset", type=Path, required=True)
    evaluate.add_argument("--prompt", type=Path, required=True)
    evaluate.add_argument("--split", default="validation")
    evaluate.add_argument("--evaluation-replicates", type=int, default=1)

    tune = commands.add_parser("optimize", help="Run GEPA using the configured LLM")
    tune.add_argument("--dataset", type=Path, required=True)
    tune.add_argument("--prompt", type=Path, required=True)
    tune.add_argument(
        "--holdout-split", default="test",
        help="Locked split used only for final promotion (falls back to validation if absent)",
    )
    tune.add_argument("--evaluation-replicates", type=int, default=1)
    tune.add_argument("--reflection-temperature", type=float, default=0.7)
    budget = tune.add_mutually_exclusive_group()
    budget.add_argument(
        "--auto",
        choices=("light", "medium", "heavy"),
        help="Let GEPA choose its optimization budget (default: medium)",
    )
    budget.add_argument(
        "--max-metric-calls",
        type=int,
        help="Set an explicit maximum number of prompt-symbol evaluations",
    )
    return result


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def should_promote(*, optimized_mean: float, baseline_mean: float) -> bool:
    return optimized_mean > baseline_mean


def _top_isort_targets(coverage_path: Path, *, seed: int = 7) -> list[dict]:
    with coverage_path.open(encoding="utf-8") as file:
        report = json.load(file)
    ranked = []
    for source_file, file_data in report.get("files", {}).items():
        for symbol, function in file_data.get("functions", {}).items():
            branches = int(function.get("summary", {}).get("num_branches", 0))
            if symbol and branches:
                normalized = source_file.replace("\\", "/")
                marker = "/isort/isort/"
                source = "isort/" + normalized.split(marker, 1)[1] if marker in normalized else normalized
                # Vendored code is not a stable optimization target: projects often
                # omit it from coverage and its import path can vary by Python version.
                if source.startswith("isort/_vendored/"):
                    continue
                ranked.append((branches, source, symbol))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    if len(ranked) < 45:
        raise ValueError(f"Coverage report has only {len(ranked)} branch-bearing functions")
    selected = ranked[:45]
    random.Random(seed).shuffle(selected)
    return [
        {
            "project": "isort",
            "source_file": source,
            "symbol": symbol,
            "split": (
                "train" if index < 25 else "validation" if index < 35 else "test"
            ),
        }
        for index, (_, source, symbol) in enumerate(selected)
    ]


def make_runner(args: argparse.Namespace) -> CoverUpExperimentRunner:
    if args.max_attempts < 1:
        raise ValueError("--max-attempts must be at least 1")
    if args.repeat_tests < 0:
        raise ValueError("--repeat-tests cannot be negative")
    if args.max_concurrency < 1:
        raise ValueError("--max-concurrency must be at least 1")
    if args.rate_limit is not None and args.rate_limit < 1:
        raise ValueError("--rate-limit must be at least 1")
    root = args.project_root.resolve()
    provider = resolve_model_provider()
    config = ExperimentConfig(
        project_root=root,
        package_dir=_resolve(root, args.package_dir),
        tests_dir=_resolve(root, args.tests_dir),
        artifacts_dir=_resolve(root, args.artifacts_dir),
        coverup_model=provider.generation_model,
        max_attempts=args.max_attempts,
        repeat_tests=args.repeat_tests,
        max_concurrency=args.max_concurrency,
        rate_limit=args.rate_limit,
        pytest_args=args.pytest_args,
    )
    for name, path in (("package", config.package_dir), ("tests", config.tests_dir)):
        if not path.is_dir():
            raise FileNotFoundError(f"The {name} directory does not exist: {path}")
    return CoverUpExperimentRunner(config)


def init_files(args: argparse.Namespace) -> None:
    root = args.project_root.resolve()
    artifacts = _resolve(root, args.artifacts_dir)
    prompt = artifacts / "prompts" / "gpt_v2_baseline.json"
    dataset = artifacts / "datasets" / "isort_symbols.jsonl"
    if not args.force and (prompt.exists() or dataset.exists()):
        raise FileExistsError("Initialization files already exist; pass --force to replace them")
    baseline_bundle().save(prompt)
    dataset.parent.mkdir(parents=True, exist_ok=True)
    samples = _top_isort_targets(root / "src" / "coverage.json")
    dataset.write_text("".join(json.dumps(item) + "\n" for item in samples), encoding="utf-8")
    print(f"Created {prompt}")
    print(f"Created {dataset}")


def evaluate(args: argparse.Namespace) -> None:
    runner = make_runner(args)
    prompt = PromptBundle.load(args.prompt.resolve())
    if error := validate_bundle(prompt):
        raise ValueError(error)
    targets = load_targets(args.dataset.resolve(), args.split)
    if not targets:
        raise ValueError(f"No targets found for split {args.split!r}")
    batch = evaluate_bundle_repeated(
        runner, targets, prompt,
        runner.config.artifacts_dir.resolve() / "candidates",
        split=args.split,
        replicates=args.evaluation_replicates,
    )
    aggregate = batch.get("aggregate") or aggregate_coverage_score(batch["results"])
    print(json.dumps({
        "runs": batch["run_ids"],
        "aggregate_score": aggregate["score"],
        "aggregate_coverage": aggregate,
        "results": batch["results"],
    }, indent=2))


def tune(args: argparse.Namespace) -> None:
    load_dotenv(args.project_root.resolve() / ".env")
    runner = make_runner(args)
    provider = resolve_model_provider()
    baseline = PromptBundle.load(args.prompt.resolve())
    train = load_targets(args.dataset.resolve(), "train")
    validation = load_targets(args.dataset.resolve(), "validation")
    if not train or not validation:
        raise ValueError("GEPA requires at least one train and one validation target")
    holdout = load_targets(args.dataset.resolve(), args.holdout_split)
    final_targets = holdout or validation
    final_split = args.holdout_split if holdout else "validation"
    lm = dspy.LM(
        provider.optimization_model,
        max_tokens=8192,
        temperature=args.reflection_temperature,
    )
    artifacts = runner.config.artifacts_dir.resolve()
    existing_baseline_reference = None
    if args.baseline_tests_dir is not None:
        baseline_tests_dir = _resolve(
            args.project_root.resolve(), args.baseline_tests_dir
        ).resolve()
        if not baseline_tests_dir.is_dir():
            raise FileNotFoundError(
                f"The baseline tests directory does not exist: {baseline_tests_dir}"
            )
        baseline_record = runner.evaluate_existing_tests_batch(
            final_targets,
            baseline_tests_dir,
            split=final_split,
        )
        baseline_results = [
            {
                "target": result.target.__dict__,
                "run_id": baseline_record.run_id,
                "score": float(result.score["score"]) if result.score else 0.0,
                "coverage": result.score,
                "feedback": result.feedback,
            }
            for result in baseline_record.results
        ]
        baseline_evaluation = {
            "run_id": baseline_record.run_id,
            "tests_workspace": baseline_record.tests_workspace,
            "results": baseline_results,
            "aggregate": aggregate_coverage_score(baseline_results),
        }
        existing_baseline_reference = baseline_evaluation

    optimized = optimize(
        runner=runner, train_targets=train, validation_targets=validation,
        baseline=baseline, reflection_lm=lm, artifacts_dir=artifacts,
        auto=args.auto or ("medium" if args.max_metric_calls is None else None),
        max_metric_calls=args.max_metric_calls,
        evaluation_replicates=args.evaluation_replicates,
    )
    program_path = artifacts / "optimized_program.json"
    program_path.write_text(
        json.dumps(optimized.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    proposed_prompt = optimized.best_bundle
    if error := validate_bundle(proposed_prompt):
        raise ValueError(f"GEPA produced an invalid final prompt bundle: {error}")
    proposed_path = artifacts / "prompts" / "gepa_proposed.json"
    proposed_prompt.save(proposed_path)

    baseline_evaluation = evaluate_bundle_repeated(
        runner,
        final_targets,
        baseline,
        artifacts / "candidates",
        split=final_split,
        workspace_kind="baseline",
        replicates=args.evaluation_replicates,
    )
    baseline_results = baseline_evaluation["results"]
    validate_reference_evaluation(
        baseline_results, split=final_split, expected_targets=final_targets,
    )
    baseline_aggregate = baseline_evaluation["aggregate"]
    baseline_mean_score = float(baseline_aggregate["score"])
    proposed_evaluation = evaluate_bundle_repeated(
        runner,
        final_targets,
        proposed_prompt,
        artifacts / "candidates",
        split=final_split,
        workspace_kind=(
            "baseline"
            if bundle_digest(proposed_prompt) == bundle_digest(baseline)
            else "candidate"
        ),
        replicates=args.evaluation_replicates,
        reference_results=baseline_results,
    )
    validation_results = proposed_evaluation["results"]
    optimized_aggregate = proposed_evaluation["aggregate"]
    mean_score = float(optimized_aggregate["score"])
    promoted = should_promote(
        optimized_mean=mean_score,
        baseline_mean=baseline_mean_score,
    )
    production_prompt = proposed_prompt if promoted else baseline
    final_path = artifacts / "prompts" / "gepa_optimized.json"
    production_prompt.save(final_path)
    report = {
        "mean_score": mean_score,
        "baseline_mean_score": baseline_mean_score,
        "optimized_mean_score": mean_score,
        "baseline_aggregate_coverage": baseline_aggregate,
        "optimized_aggregate_coverage": optimized_aggregate,
        "absolute_gain": mean_score - baseline_mean_score,
        "promoted": promoted,
        "final_split": final_split,
        "used_locked_holdout": bool(holdout),
        "evaluation_replicates": args.evaluation_replicates,
        "prompt": str(proposed_path),
        "production_prompt": str(final_path),
        "baseline_prompt": str(args.prompt.resolve()),
        "baseline_tests_workspaces": baseline_evaluation["tests_workspaces"],
        "baseline_run_ids": baseline_evaluation["run_ids"],
        "run_ids": proposed_evaluation["run_ids"],
        "tests_workspaces": proposed_evaluation["tests_workspaces"],
        "baseline_results": baseline_results,
        "results": validation_results,
        "existing_baseline_reference": existing_baseline_reference,
    }
    report_path = artifacts / "final_validation.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved optimized program to {program_path}")
    print(f"Final comparison split: {final_split}")
    print(f"Baseline aggregate score: {baseline_mean_score:.4f}")
    print(f"GEPA proposal aggregate score: {mean_score:.4f}")
    print(f"Absolute gain: {mean_score - baseline_mean_score:.4f}")
    if promoted:
        print(f"Promoted GEPA proposal to {final_path}")
    else:
        print(f"GEPA proposal did not improve; retained baseline at {final_path}")


def main() -> None:
    # Load model defaults before argparse evaluates environment-backed options.
    load_dotenv(Path.cwd() / ".env")
    args = parser().parse_args()
    if args.command == "init":
        init_files(args)
    elif args.command == "evaluate":
        evaluate(args)
    else:
        tune(args)


if __name__ == "__main__":
    main()
