from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

import dspy
from dotenv import load_dotenv

from .archive import build_candidate_test_archive
from .dataset import load_targets, validate_project_stratification
from .gepa import (
    build_coverage_report,
    bundle_digest,
    evaluate_bundle_repeated,
    optimize,
    rerank_prompt_candidates,
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
    result.add_argument(
        "--target-context",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Include exact target contract context",
    )
    result.add_argument(
        "--repository-test-context",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Include relevant existing tests/fixtures when target context is enabled",
    )
    result.add_argument(
        "--target-context-max-chars",
        type=int,
        default=6_000,
        help="Maximum repository-local context characters per target",
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
    tune.add_argument(
        "--rerank-top-k",
        type=int,
        default=0,
        help=(
            "Rerank this many finalists (including the mandatory baseline) on "
            "validation before opening holdout; 0 disables reranking"
        ),
    )
    tune.add_argument(
        "--rerank-replicates",
        type=int,
        default=3,
        help="Independent validation generations per rerank finalist (default: 3)",
    )
    tune.add_argument(
        "--rerank-length-penalty-per-1k",
        type=float,
        default=0.0,
        help="Coverage score penalty per 1,000 prompt chars above baseline",
    )
    tune.add_argument(
        "--rerank-max-prompt-chars",
        type=int,
        help="Discard non-baseline rerank candidates above this total char cap",
    )
    tune.add_argument(
        "--search-only",
        action="store_true",
        help="Save GEPA candidates without evaluating or opening the final holdout",
    )
    tune.add_argument(
        "--program-output",
        type=Path,
        help="Optional optimized-program output path, useful for multi-seed search",
    )
    tune.add_argument("--reflection-temperature", type=float, default=0.7)
    tune.add_argument(
        "--best-candidate-probability",
        type=float,
        default=0.7,
        help=(
            "Probability of mutating the aggregate current-best candidate; "
            "0 selects pure Pareto exploration (default: 0.7)"
        ),
    )
    tune.add_argument(
        "--gepa-seed",
        type=int,
        default=7,
        help="Seed for GEPA candidate selection and search (default: 7)",
    )
    tune.add_argument(
        "--reflection-minibatch-size",
        type=int,
        default=8,
        help="Maximum train examples reflected on per GEPA proposal (default: 8)",
    )
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

    rerank = commands.add_parser(
        "rerank",
        help="Rerank candidates from a saved GEPA program on validation only",
    )
    rerank.add_argument("--dataset", type=Path, required=True)
    rerank.add_argument("--prompt", type=Path, required=True)
    rerank.add_argument(
        "--optimized-program",
        type=Path,
        action="append",
        required=True,
        help="Saved GEPA program; repeat this option to pool multiple seeds",
    )
    rerank.add_argument("--split", choices=("validation",), default="validation")
    rerank.add_argument("--top-k", type=int, default=5)
    rerank.add_argument("--replicates", type=int, default=3)
    rerank.add_argument("--length-penalty-per-1k", type=float, default=0.0)
    rerank.add_argument("--max-prompt-chars", type=int)
    rerank.add_argument("--report-output", type=Path)
    rerank.add_argument("--output-prompt", type=Path)

    archive = commands.add_parser(
        "archive",
        help="Build a split-locked greedy archive from cached generated tests",
    )
    archive.add_argument("--output-dir", type=Path, required=True)
    archive.add_argument("--split", choices=("train", "validation", "test"), default="validation")
    archive.add_argument("--evaluation-digest")
    archive.add_argument(
        "--source-replicate",
        dest="source_replicates",
        type=int,
        action="append",
        help="Only archive tests from this generation replicate; may be repeated",
    )
    archive.add_argument(
        "--allow-holdout",
        action="store_true",
        help="Allow a final report on test; never use it to tune the archive",
    )
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


def build_archive(args: argparse.Namespace) -> None:
    root = args.project_root.resolve()
    report = build_candidate_test_archive(
        project_root=root,
        artifacts_dir=_resolve(root, args.artifacts_dir),
        output_dir=_resolve(root, args.output_dir),
        sample_repos_dir=_resolve(root, args.sample_repos_dir),
        split=args.split,
        evaluation_digest=args.evaluation_digest,
        source_replicates=(
            set(args.source_replicates) if args.source_replicates is not None else None
        ),
        allow_holdout=args.allow_holdout,
        pytest_args=args.pytest_args,
        repeat_tests=args.repeat_tests,
    )
    verification = report["verification"]
    print(json.dumps({
        "split": report["split"],
        "evaluation_digest": report["evaluation_digest"],
        "source_replicates": report["source_replicates"],
        "candidate_test_count": report["candidate_test_count"],
        "selected_test_count": report["selected_test_count"],
        "verified": verification["verified"],
        "repeat_tests": verification["repeat_tests"],
        "archive_aggregate": verification["aggregate"],
        "verified_gain_vs_best_single": report["verified_gain_vs_best_single"],
    }, indent=2))


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
    artifacts directory. A bundled upstream ``tests`` directory is optional,
    read-only context and must not be required for prompt optimization.
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
    if args.target_context_max_chars < 0:
        raise ValueError("--target-context-max-chars cannot be negative")
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
        target_context=args.target_context,
        target_context_max_chars=args.target_context_max_chars,
        repository_test_context=args.repository_test_context,
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


def rerank_saved_program(args: argparse.Namespace) -> None:
    """Select a stable validation winner without rerunning GEPA search."""
    root = args.project_root.resolve()
    load_dotenv(root / ".env")
    baseline = PromptBundle.load(_resolve(root, args.prompt).resolve())
    configured_programs = args.optimized_program
    if isinstance(configured_programs, Path):
        configured_programs = [configured_programs]
    program_paths = [_resolve(root, path).resolve() for path in configured_programs]
    candidates: list[PromptBundle] = []
    validation_scores: list[float] = []
    optimizer_configs = []
    seeds = []
    for program_path in program_paths:
        program = json.loads(program_path.read_text(encoding="utf-8"))
        candidate_values = program.get("candidates")
        candidate_scores = program.get("validation_scores")
        if not isinstance(candidate_values, list) or not isinstance(
            candidate_scores, list
        ):
            raise ValueError(
                f"{program_path} must contain candidate and validation score lists"
            )
        if len(candidate_values) != len(candidate_scores):
            raise ValueError(
                f"{program_path} candidate and validation score counts differ"
            )
        candidates.extend(
            PromptBundle.from_candidate(value) for value in candidate_values
        )
        validation_scores.extend(float(value) for value in candidate_scores)
        config = program.get("optimizer_config")
        if isinstance(config, dict):
            optimizer_configs.append(config)
            if "gepa_seed" in config:
                seeds.append(int(config["gepa_seed"]))
    allowed_variations = {"gepa_seed", "best_candidate_probability"}
    comparable_configs = {
        json.dumps(
            {
                key: value
                for key, value in config.items()
                if key not in allowed_variations
            },
            sort_keys=True,
        )
        for config in optimizer_configs
    }
    if len(comparable_configs) > 1:
        raise ValueError(
            "Pooled programs must use the same optimizer configuration except "
            "gepa_seed and best_candidate_probability"
        )
    targets = load_targets(_resolve(root, args.dataset).resolve(), args.split)
    if not targets:
        raise ValueError(f"No targets found for split {args.split!r}")
    projects = _resolve_project_layouts(root, targets, _sample_repos_dir(args))
    runner = make_runner(args, projects=projects)
    artifacts = runner.config.artifacts_dir.resolve()
    result = rerank_prompt_candidates(
        runner=runner,
        validation_targets=targets,
        baseline=baseline,
        candidates=candidates,
        validation_scores=validation_scores,
        candidate_dir=artifacts / "candidates",
        top_k=args.top_k,
        replicates=args.replicates,
        split=args.split,
        length_penalty_per_1k=float(
            getattr(args, "length_penalty_per_1k", 0.0)
        ),
        max_prompt_chars=getattr(args, "max_prompt_chars", None),
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    configured_report_output = getattr(args, "report_output", None)
    report_path = (
        _resolve(root, configured_report_output).resolve()
        if configured_report_output is not None
        else artifacts / "candidate_rerank.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        **result.as_dict(),
        "source_programs": [str(path) for path in program_paths],
        "gepa_seeds": seeds,
        "optimizer_configs": optimizer_configs,
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    output_prompt = (
        _resolve(root, args.output_prompt).resolve()
        if args.output_prompt is not None
        else artifacts / "prompts" / "gepa_reranked.json"
    )
    result.selected_bundle.save(output_prompt)
    print(f"Saved candidate rerank report to {report_path}")
    print(f"Selected validation winner at {output_prompt}")
    for row in result.leaderboard:
        print(
            f"  #{row['rank']} {row['digest']} mean={row['mean_score']:.4f} "
            f"selection={row['selection_score']:.4f} "
            f"std={row['score_stddev']:.4f} failures={row['failure_rate']:.2%}"
        )


def tune(args: argparse.Namespace) -> None:
    root = args.project_root.resolve()
    load_dotenv(root / ".env")
    search_only = bool(getattr(args, "search_only", False))
    if search_only and int(getattr(args, "rerank_top_k", 0)):
        raise ValueError("--search-only cannot be combined with --rerank-top-k")
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
    baseline_evaluation = None
    baseline_results = None
    baseline_aggregate = None
    baseline_mean_score = None
    if not search_only:
        if args.baseline_tests_dir is not None:
            baseline_tests_dir = _resolve(root, args.baseline_tests_dir).resolve()
            if not baseline_tests_dir.is_dir():
                raise FileNotFoundError(
                    f"The baseline tests directory does not exist: {baseline_tests_dir}"
                )
            baseline_record = runner.evaluate_existing_tests_batch(
                final_targets,
                baseline_tests_dir,
                split=final_split,
            )
            historical_results = [
                {
                    "target": result.target.__dict__,
                    "run_id": baseline_record.run_id,
                    "score": float(result.score["score"]) if result.score else 0.0,
                    "coverage": result.score,
                    "feedback": result.feedback,
                }
                for result in baseline_record.results
            ]
            existing_baseline_reference = {
                "run_id": baseline_record.run_id,
                "tests_workspace": baseline_record.tests_workspace,
                "results": historical_results,
                "aggregate": aggregate_coverage_score(historical_results),
            }

        # The final-split baseline is only needed by the promotion gate. Search-only
        # multi-seed runs must not inspect the locked holdout.
        baseline_evaluation = evaluate_bundle_repeated(
            runner,
            final_targets,
            baseline,
            artifacts / "candidates",
            split=final_split,
            workspace_kind="baseline",
            replicates=args.evaluation_replicates,
        )
        baseline_results = [
            dict(result) for result in baseline_evaluation["results"]
        ]
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
        gepa_seed=args.gepa_seed,
        reflection_minibatch_size=args.reflection_minibatch_size,
        reflection_temperature=args.reflection_temperature,
        best_candidate_probability=float(
            getattr(args, "best_candidate_probability", 0.7)
        ),
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    configured_program_output = getattr(args, "program_output", None)
    program_path = (
        _resolve(root, configured_program_output).resolve()
        if configured_program_output is not None
        else artifacts / "optimized_program.json"
    )
    program_path.parent.mkdir(parents=True, exist_ok=True)
    program_path.write_text(
        json.dumps(optimized.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if search_only:
        print(f"Saved search-only GEPA program to {program_path}")
        print("Locked holdout was not evaluated.")
        return

    assert baseline_evaluation is not None
    assert baseline_results is not None
    assert baseline_aggregate is not None
    assert baseline_mean_score is not None
    rerank_top_k = int(getattr(args, "rerank_top_k", 0))
    rerank_replicates = int(getattr(args, "rerank_replicates", 3))
    rerank_length_penalty = float(
        getattr(args, "rerank_length_penalty_per_1k", 0.0)
    )
    rerank_max_prompt_chars = getattr(args, "rerank_max_prompt_chars", None)
    if rerank_top_k < 0:
        raise ValueError("--rerank-top-k cannot be negative")
    candidate_rerank = None
    proposed_prompt = optimized.best_bundle
    if rerank_top_k:
        reranked = rerank_prompt_candidates(
            runner=runner,
            validation_targets=validation,
            baseline=baseline,
            candidates=optimized.candidates,
            validation_scores=optimized.validation_scores,
            candidate_dir=artifacts / "candidates",
            top_k=rerank_top_k,
            replicates=rerank_replicates,
            split="validation",
            length_penalty_per_1k=rerank_length_penalty,
            max_prompt_chars=rerank_max_prompt_chars,
        )
        candidate_rerank = reranked.as_dict()
        (artifacts / "candidate_rerank.json").write_text(
            json.dumps(candidate_rerank, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        reranked.selected_bundle.save(
            artifacts / "prompts" / "gepa_reranked.json"
        )
        proposed_prompt = reranked.selected_bundle
        print(
            "Reranked "
            f"{reranked.top_k} finalists over {reranked.replicates} validation "
            f"replicates; selected {bundle_digest(proposed_prompt)}."
        )
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
            "candidate_rerank": candidate_rerank,
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
        "candidate_rerank": candidate_rerank,
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


def _repeat_final_baseline(
    runner: CoverUpExperimentRunner,
    targets: list[SymbolTarget],
    baseline: PromptBundle,
    candidate_dir: Path,
    *,
    split: str,
    replicates: int,
    reference_rows: list[dict],
) -> dict:
    """Use the same generation replicate count for both sides of a final gate."""
    if replicates == 1:
        return {
            "results": reference_rows,
            "aggregate": aggregate_coverage_score(reference_rows),
            "run_ids": [],
            "tests_workspaces": [],
        }
    return evaluate_bundle_repeated(
        runner,
        targets,
        baseline,
        candidate_dir,
        split=split,
        workspace_kind="baseline",
        replicates=replicates,
        reference_results=reference_rows,
    )


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
    baseline_evaluation = _repeat_final_baseline(
        runner,
        final_targets,
        baseline,
        artifacts / "candidates",
        split=args.holdout_split,
        replicates=args.evaluation_replicates,
        reference_rows=rows,
    )
    rows = baseline_evaluation["results"]
    baseline_aggregate = baseline_evaluation["aggregate"]
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
            *(
                baseline_evaluation["tests_workspaces"]
                if args.evaluation_replicates > 1
                else [*reference.get("tests_workspaces", []), *repaired_workspaces]
            ),
        ],
        "baseline_run_ids": [
            *(
                baseline_evaluation["run_ids"]
                if args.evaluation_replicates > 1
                else [*reference.get("run_ids", []), *repaired_run_ids]
            ),
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
            "paired_baseline_replicates": args.evaluation_replicates,
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
    elif args.command == "rerank":
        rerank_saved_program(args)
    elif args.command == "archive":
        build_archive(args)
    elif args.command == "finalize":
        finalize(args)
    else:  # pragma: no cover - argparse requires a known command
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
