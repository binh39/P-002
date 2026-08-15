from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

import dspy
from dotenv import load_dotenv

from .dataset import load_targets, validate_project_stratification
from .gepa import (
    build_coverage_report,
    bundle_digest,
    evaluate_bundle_repeated,
    optimize,
    validate_bundle,
    validate_reference_evaluation,
)
from .metrics import aggregate_coverage_score
from .models import ExperimentConfig, ProjectLayout, SymbolTarget
from .prompts import PromptBundle, baseline_bundle
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
    result.add_argument(
        "--sample-repos-dir",
        type=Path,
        default=Path("src/sample_repo"),
        help=(
            "Directory containing one subdirectory per project; used to resolve "
            "per-project package/tests layouts for multi-project datasets"
        ),
    )
    result.add_argument("--artifacts-dir", type=Path, default=Path("eval/prompt_optimization"))
    result.add_argument("--max-attempts", type=int, default=3)
    result.add_argument(
        "--repeat-tests", type=int, default=5,
        help="Repeat generated tests to reject flaky suites (default: 5)",
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

    tune = commands.add_parser("optimize", help="Run GEPA using Gemini")
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

    finalize = commands.add_parser(
        "finalize",
        help="Finish the locked holdout comparison from a saved GEPA proposal",
    )
    finalize.add_argument("--dataset", type=Path, required=True)
    finalize.add_argument("--prompt", type=Path, required=True)
    finalize.add_argument("--proposed-prompt", type=Path, required=True)
    finalize.add_argument(
        "--reference-cache",
        type=Path,
        required=True,
        help=(
            "Saved full-split baseline batch. Invalid rows are regenerated and "
            "merged; valid rows are reused without rerunning GEPA."
        ),
    )
    finalize.add_argument("--holdout-split", default="test")
    finalize.add_argument("--evaluation-replicates", type=int, default=1)
    return result


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _model_from_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured. Add it to .env before running the pipeline.")
    return value


def should_promote(*, optimized_mean: float, baseline_mean: float) -> bool:
    return optimized_mean > baseline_mean


def _print_coverage_report(report: dict) -> None:
    """Print a compact per-split, per-prompt coverage summary table."""
    header = f"{'split':<12}{'prompt':<10}{'stmt%':>8}{'branch%':>9}{'score':>8}"
    print(header)
    print("-" * len(header))
    for split, entries in report["splits"].items():
        for prompt in ("baseline", "optimized"):
            row = entries[prompt]
            print(
                f"{split:<12}{prompt:<10}"
                f"{row['statement_coverage'] * 100:>7.2f}%"
                f"{row['branch_coverage'] * 100:>8.2f}%"
                f"{row['score']:>8.4f}"
            )


def _top_isort_targets(coverage_path: Path, *, seed: int = 7) -> list[dict]:
    with coverage_path.open(encoding="utf-8") as file:
        report = json.load(file)
    ranked = []
    for source_file, file_data in report.get("files", {}).items():
        normalized = source_file.replace("\\", "/")
        marker = "/isort/isort/"
        if marker not in normalized:
            continue
        source = "isort/" + normalized.split(marker, 1)[1]
        if source.startswith("isort/_vendored/"):
            continue
        for symbol, function in file_data.get("functions", {}).items():
            statements = int(function.get("summary", {}).get("num_statements", 0))
            branches = int(function.get("summary", {}).get("num_branches", 0))
            if symbol and statements:
                # Prefer every branch-bearing target, then use statement-heavy
                # branchless functions to reach the requested benchmark size.
                ranked.append((branches > 0, branches, statements, source, symbol))
    ranked.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3], item[4]))
    if len(ranked) < 110:
        raise ValueError(
            f"Coverage report has only {len(ranked)} measurable isort functions; "
            "110 are required"
        )
    selected = ranked[:110]
    random.Random(seed).shuffle(selected)
    return [
        {
            "project": "isort",
            "source_file": source,
            "symbol": symbol,
            "split": (
                "train" if index < 50 else "validation" if index < 80 else "test"
            ),
        }
        for index, (_, _, _, source, symbol) in enumerate(selected)
    ]


def _resolve_project_layouts(
    root: Path,
    targets: list[SymbolTarget],
    sample_repos_dir: Path,
) -> dict[str, ProjectLayout] | None:
    """Resolve bundled source packages for every dataset project.

    CoverUp evaluates each target in a generated-test workspace under the
    artifacts directory.  A bundled upstream ``tests`` directory is therefore
    metadata only and must not be required for prompt optimization.
    """
    projects = sorted({target.project for target in targets})
    repos = _resolve(root, sample_repos_dir)
    layouts: dict[str, ProjectLayout] = {}
    for project in projects:
        package = (repos / project / project).resolve()
        tests = (repos / project / "tests").resolve()
        if not package.is_dir():
            raise FileNotFoundError(
                f"Optimization run needs package directory {package}"
            )
        layouts[project] = ProjectLayout(package_dir=package, tests_dir=tests)
    return layouts


def _sample_repos_dir(args: argparse.Namespace) -> Path:
    return getattr(args, "sample_repos_dir", Path("src/sample_repo"))


def make_runner(
    args: argparse.Namespace,
    projects: dict[str, ProjectLayout] | None = None,
) -> CoverUpExperimentRunner:
    if args.max_attempts < 1:
        raise ValueError("--max-attempts must be at least 1")
    if args.repeat_tests < 0:
        raise ValueError("--repeat-tests cannot be negative")
    if args.max_concurrency < 1:
        raise ValueError("--max-concurrency must be at least 1")
    if args.rate_limit is not None and args.rate_limit < 1:
        raise ValueError("--rate-limit must be at least 1")
    root = args.project_root.resolve()
    config = ExperimentConfig(
        project_root=root,
        package_dir=_resolve(root, args.package_dir),
        tests_dir=_resolve(root, args.tests_dir),
        artifacts_dir=_resolve(root, args.artifacts_dir),
        coverup_model=_model_from_env("COVERUP_MODEL"),
        max_attempts=args.max_attempts,
        repeat_tests=args.repeat_tests,
        max_concurrency=args.max_concurrency,
        rate_limit=args.rate_limit,
        pytest_args=args.pytest_args,
        projects=projects,
    )
    # ``package_dir`` is only the single-project fallback. Dynamic and
    # multi-project runs have already validated every entry in ``projects``.
    if projects is None and not config.package_dir.is_dir():
        raise FileNotFoundError(
            f"The package directory does not exist: {config.package_dir}"
        )
    return CoverUpExperimentRunner(config)


def init_files(args: argparse.Namespace) -> None:
    root = args.project_root.resolve()
    artifacts = _resolve(root, args.artifacts_dir)
    prompt = artifacts / "prompts" / "gpt_v2_baseline.json"
    dataset = artifacts / "datasets" / "isort_mlxtend_symbols.jsonl"
    if not args.force and (prompt.exists() or dataset.exists()):
        raise FileExistsError("Initialization files already exist; pass --force to replace them")
    baseline_bundle().save(prompt)
    dataset.parent.mkdir(parents=True, exist_ok=True)
    samples = _top_isort_targets(root / "src" / "coverage.json")
    dataset.write_text("".join(json.dumps(item) + "\n" for item in samples), encoding="utf-8")
    print(f"Created {prompt}")
    print(f"Created {dataset}")


def evaluate(args: argparse.Namespace) -> None:
    prompt = PromptBundle.load(args.prompt.resolve())
    if error := validate_bundle(prompt):
        raise ValueError(error)
    targets = load_targets(args.dataset.resolve(), args.split)
    if not targets:
        raise ValueError(f"No targets found for split {args.split!r}")
    projects = _resolve_project_layouts(
        args.project_root.resolve(), targets, _sample_repos_dir(args)
    )
    runner = make_runner(args, projects=projects)
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
    baseline = PromptBundle.load(args.prompt.resolve())
    train = load_targets(args.dataset.resolve(), "train")
    validation = load_targets(args.dataset.resolve(), "validation")
    if not train or not validation:
        raise ValueError("GEPA requires at least one train and one validation target")
    holdout = load_targets(args.dataset.resolve(), args.holdout_split)
    projects = _resolve_project_layouts(
        args.project_root.resolve(),
        [*train, *validation, *holdout],
        _sample_repos_dir(args),
    )
    runner = make_runner(args, projects=projects)
    final_targets = holdout or validation
    final_split = args.holdout_split if holdout else "validation"
    validate_project_stratification({
        "train": train,
        "validation": validation,
        final_split: final_targets,
    })
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

    # Measure the locked final-split baseline before starting GEPA. This result
    # is cached and reused at the promotion gate, so a broken holdout target
    # fails early instead of wasting the entire search budget first.
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

    lm = dspy.LM(
        _model_from_env("OPTIMIZE_MODEL"),
        max_tokens=8192,
        temperature=args.reflection_temperature,
    )

    optimized = optimize(
        runner=runner, train_targets=train, validation_targets=validation,
        baseline=baseline, reflection_lm=lm, artifacts_dir=artifacts,
        auto=args.auto or ("medium" if args.max_metric_calls is None else None),
        max_metric_calls=args.max_metric_calls,
        evaluation_replicates=args.evaluation_replicates,
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    program_path = artifacts / "optimized_program.json"
    program_path.write_text(
        json.dumps(optimized.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    proposed_prompt = optimized.best_bundle
    if error := validate_bundle(proposed_prompt):
        raise ValueError(f"GEPA produced an invalid final prompt bundle: {error}")
    proposed_path = artifacts / "prompts" / "gepa_proposed.json"
    proposed_prompt.save(proposed_path)

    if bundle_digest(proposed_prompt) == bundle_digest(baseline):
        final_path = artifacts / "prompts" / "gepa_optimized.json"
        baseline.save(final_path)
        report = {
            "mean_score": None,
            "baseline_mean_score": baseline_mean_score,
            "optimized_mean_score": None,
            "baseline_aggregate_coverage": baseline_aggregate,
            "optimized_aggregate_coverage": None,
            "absolute_gain": None,
            "promoted": False,
            "final_evaluation_skipped": True,
            "skip_reason": (
                "GEPA selected the unchanged baseline; there is no new prompt "
                "to compare on the final split."
            ),
            "final_split": final_split,
            "used_locked_holdout": bool(holdout),
            "evaluation_replicates": args.evaluation_replicates,
            "prompt": str(proposed_path),
            "production_prompt": str(final_path),
            "baseline_prompt": str(args.prompt.resolve()),
            "baseline_tests_workspaces": baseline_evaluation["tests_workspaces"],
            "baseline_run_ids": baseline_evaluation["run_ids"],
            "run_ids": [],
            "tests_workspaces": [],
            "baseline_results": baseline_results,
            "results": [],
            "existing_baseline_reference": existing_baseline_reference,
        }
        report_path = artifacts / "final_validation.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Saved optimized program to {program_path}")
        print(
            "GEPA retained the unchanged baseline; skipped final "
            f"{final_split} test generation and evaluation."
        )
        print(f"Retained baseline at {final_path}")
        return

    proposed_evaluation = evaluate_bundle_repeated(
        runner,
        final_targets,
        proposed_prompt,
        artifacts / "candidates",
        split=final_split,
        workspace_kind="candidate",
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
        "final_evaluation_skipped": False,
        "skip_reason": None,
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

    targets_by_split = {"train": train, "validation": validation}
    if final_split not in targets_by_split:
        targets_by_split[final_split] = final_targets
    coverage_report = build_coverage_report(
        runner,
        targets_by_split=targets_by_split,
        baseline=baseline,
        optimized=proposed_prompt,
        candidate_dir=artifacts / "candidates",
        evaluation_replicates=args.evaluation_replicates,
    )
    coverage_report_path = artifacts / "coverage_report.json"
    coverage_report_path.write_text(
        json.dumps(coverage_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved coverage report to {coverage_report_path}")
    _print_coverage_report(coverage_report)


def _target_key(value: SymbolTarget | dict) -> tuple[str, str, str, str]:
    target = value.__dict__ if isinstance(value, SymbolTarget) else value
    return (
        str(target["project"]), str(target["source_file"]),
        str(target["symbol"]), str(target["split"]),
    )


def _reference_row_is_valid(row: dict) -> bool:
    coverage = row.get("coverage")
    if not coverage or coverage.get("valid") is False:
        return False
    try:
        return int(coverage["num_statements"]) > 0 and int(
            coverage["num_branches"]
        ) >= 0
    except (KeyError, TypeError, ValueError):
        return False


def _coverage_summary(aggregate: dict, count: int) -> dict:
    return {
        "num_targets": count,
        "score": float(aggregate.get("score", 0.0)),
        "statement_coverage": float(aggregate.get("statement_coverage", 0.0)),
        "branch_coverage": float(aggregate.get("branch_coverage", 0.0)),
        "covered_statements": int(aggregate.get("covered_statements", 0)),
        "num_statements": int(aggregate.get("num_statements", 0)),
        "covered_branches": int(aggregate.get("covered_branches", 0)),
        "num_branches": int(aggregate.get("num_branches", 0)),
    }


def finalize(args: argparse.Namespace) -> None:
    """Recover the final comparison without rerunning an expensive GEPA search."""
    load_dotenv(args.project_root.resolve() / ".env")
    baseline = PromptBundle.load(args.prompt.resolve())
    proposed = PromptBundle.load(args.proposed_prompt.resolve())
    for label, bundle in (("baseline", baseline), ("proposed", proposed)):
        if error := validate_bundle(bundle):
            raise ValueError(f"Invalid {label} prompt bundle: {error}")

    final_targets = load_targets(args.dataset.resolve(), args.holdout_split)
    if not final_targets:
        raise ValueError(f"No targets found for split {args.holdout_split!r}")
    validate_project_stratification({
        "train": load_targets(args.dataset.resolve(), "train"),
        "validation": load_targets(args.dataset.resolve(), "validation"),
        args.holdout_split: final_targets,
    })
    projects = _resolve_project_layouts(
        args.project_root.resolve(), final_targets, _sample_repos_dir(args)
    )
    runner = make_runner(args, projects=projects)
    artifacts = runner.config.artifacts_dir.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)

    reference = json.loads(args.reference_cache.resolve().read_text(encoding="utf-8"))
    rows = list(reference.get("results", []))
    expected = {_target_key(target) for target in final_targets}
    actual = {_target_key(row["target"]) for row in rows}
    if actual != expected:
        raise RuntimeError(
            "Reference cache target set does not match the requested holdout split."
        )
    invalid_keys = {
        _target_key(row["target"]) for row in rows if not _reference_row_is_valid(row)
    }
    repaired_run_ids: list[str] = []
    repaired_workspaces: list[str] = []
    if invalid_keys:
        invalid_targets = [
            target for target in final_targets if _target_key(target) in invalid_keys
        ]
        repaired = evaluate_bundle_repeated(
            runner,
            invalid_targets,
            baseline,
            artifacts / "candidates",
            split=args.holdout_split,
            workspace_kind="baseline",
            replicates=args.evaluation_replicates,
        )
        replacements = {
            _target_key(row["target"]): row for row in repaired["results"]
        }
        rows = [replacements.get(_target_key(row["target"]), row) for row in rows]
        repaired_run_ids = repaired["run_ids"]
        repaired_workspaces = repaired["tests_workspaces"]

    validate_reference_evaluation(
        rows, split=args.holdout_split, expected_targets=final_targets,
    )
    baseline_aggregate = aggregate_coverage_score(rows)
    proposed_evaluation = evaluate_bundle_repeated(
        runner,
        final_targets,
        proposed,
        artifacts / "candidates",
        split=args.holdout_split,
        workspace_kind="candidate",
        replicates=args.evaluation_replicates,
        reference_results=rows,
    )
    proposed_aggregate = proposed_evaluation["aggregate"]
    baseline_score = float(baseline_aggregate["score"])
    proposed_score = float(proposed_aggregate["score"])
    promoted = should_promote(
        optimized_mean=proposed_score, baseline_mean=baseline_score,
    )

    proposed_path = artifacts / "prompts" / "gepa_proposed.json"
    proposed.save(proposed_path)
    final_path = artifacts / "prompts" / "gepa_optimized.json"
    (proposed if promoted else baseline).save(final_path)
    report = {
        "mean_score": proposed_score,
        "baseline_mean_score": baseline_score,
        "optimized_mean_score": proposed_score,
        "baseline_aggregate_coverage": baseline_aggregate,
        "optimized_aggregate_coverage": proposed_aggregate,
        "absolute_gain": proposed_score - baseline_score,
        "promoted": promoted,
        "final_evaluation_skipped": False,
        "skip_reason": None,
        "final_split": args.holdout_split,
        "used_locked_holdout": True,
        "evaluation_replicates": args.evaluation_replicates,
        "prompt": str(proposed_path),
        "production_prompt": str(final_path),
        "baseline_prompt": str(args.prompt.resolve()),
        "baseline_tests_workspaces": [
            *reference.get("tests_workspaces", []), *repaired_workspaces,
        ],
        "baseline_run_ids": [
            *reference.get("run_ids", []), *repaired_run_ids,
        ],
        "run_ids": proposed_evaluation["run_ids"],
        "tests_workspaces": proposed_evaluation["tests_workspaces"],
        "baseline_results": rows,
        "results": proposed_evaluation["results"],
        "existing_baseline_reference": None,
        "recovery": {
            "source_reference_cache": str(args.reference_cache.resolve()),
            "repaired_targets": ["::".join(key[1:3]) for key in sorted(invalid_keys)],
            "gepa_search_rerun": False,
        },
    }
    (artifacts / "final_validation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    coverage_report = {
        "baseline_digest": bundle_digest(baseline),
        "optimized_digest": bundle_digest(proposed),
        "evaluation_replicates": args.evaluation_replicates,
        "recovered_final_split_only": True,
        "splits": {
            args.holdout_split: {
                "baseline": _coverage_summary(baseline_aggregate, len(rows)),
                "optimized": _coverage_summary(
                    proposed_aggregate, len(proposed_evaluation["results"])
                ),
            }
        },
    }
    (artifacts / "coverage_report.json").write_text(
        json.dumps(coverage_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Final comparison split: {args.holdout_split}")
    print(f"Repaired baseline targets: {len(invalid_keys)}")
    print(f"Baseline aggregate score: {baseline_score:.4f}")
    print(f"GEPA proposal aggregate score: {proposed_score:.4f}")
    print(f"Absolute gain: {proposed_score - baseline_score:.4f}")
    print(f"Promoted: {promoted}")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(line_buffering=True, write_through=True)
    # Load model defaults before argparse evaluates environment-backed options.
    load_dotenv(Path.cwd() / ".env")
    args = parser().parse_args()
    if args.command == "init":
        init_files(args)
    elif args.command == "evaluate":
        evaluate(args)
    elif args.command == "optimize":
        tune(args)
    else:
        finalize(args)


if __name__ == "__main__":
    main()
