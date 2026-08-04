from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path

import dspy
from dotenv import load_dotenv

from optimizer.bootstrap import compile_bootstrap
from optimizer.dataset import build_v2_splits
from optimizer.gepa import compile_gepa
from optimizer.module import TestGenReactModule
from src.optimization.provider import resolve_model_provider

from .baselines import (
    CoverUpDirectoryGenerator,
    CoverUpManifestGenerator,
    DspyModuleGenerator,
    static_symprompt_module,
    zero_shot_module,
)
from .ledger import HoldoutLedger
from .models import BaselineEvaluation, GeneratedTest
from .preflight import validate_generation_contract
from .report import generate_report
from .runner import evaluate_generator

BASELINES = (
    "zero_shot",
    "static_symprompt",
    "coverup",
    "bootstrap_few_shot",
    "gepa",
)


def _require_source_upload_consent(args: argparse.Namespace) -> None:
    """Prevent an accidental source-code transfer to an external LLM."""
    if args.baseline == "coverup":
        return
    if not args.allow_source_upload:
        raise RuntimeError(
            f"Baseline {args.baseline!r} sends focal source code, existing tests, "
            "and execution feedback to the configured LLM provider. Re-run with "
            "--allow-source-upload only after that transfer is explicitly approved."
        )


def _lm_cost(lm: dspy.LM) -> float:
    return sum(
        float(entry.get("cost") or 0.0)
        for entry in lm.history
        if isinstance(entry, dict)
    )


def _build_generator(
    args: argparse.Namespace,
    train: list,
    validation: list,
) -> tuple[Callable[[object], GeneratedTest], float, float]:
    if args.baseline == "coverup":
        if args.coverup_manifest:
            return (
                CoverUpManifestGenerator(args.coverup_manifest),
                args.coverup_cost_usd,
                args.coverup_generation_latency_seconds,
            )
        if args.coverup_tests_dir:
            return (
                CoverUpDirectoryGenerator(args.coverup_tests_dir),
                args.coverup_cost_usd,
                args.coverup_generation_latency_seconds,
            )
        raise ValueError(
            "The CoverUp baseline requires --coverup-manifest or "
            "--coverup-tests-dir from a real CoverUp run"
        )

    provider = resolve_model_provider()
    lm = dspy.LM(provider.generation_model, cache=False)
    dspy.configure(lm=lm)

    def cumulative_cost() -> float:
        return _lm_cost(lm)

    started = time.monotonic()
    before_cost = cumulative_cost()

    if args.baseline == "zero_shot":
        module = zero_shot_module()
    elif args.baseline == "static_symprompt":
        module = static_symprompt_module()
    else:
        module = TestGenReactModule(
            args.module_path,
            max_iters=args.max_iters,
        )

    preflight_generator = DspyModuleGenerator(
        module,
        cumulative_cost=cumulative_cost,
    )
    validate_generation_contract(preflight_generator, validation)

    if args.baseline == "bootstrap_few_shot":
        module = compile_bootstrap(module, train[: args.bootstrap_train_size])
    elif args.baseline == "gepa":
        module = compile_gepa(
            module,
            train,
            validation,
            reflection_lm=lm,
            auto="light",
            log_dir=str(args.gepa_log_dir),
        )

    compile_latency = time.monotonic() - started
    compile_cost = max(0.0, cumulative_cost() - before_cost)

    return (
        DspyModuleGenerator(module, cumulative_cost=cumulative_cost),
        compile_cost,
        compile_latency,
    )


def _run(args: argparse.Namespace) -> None:
    load_dotenv(args.env_file)
    train, validation, holdout = build_v2_splits(
        args.dataset,
        args.source_root,
        harness_module_path=args.module_path,
    )
    generator, compile_cost, compile_latency = _build_generator(
        args,
        train,
        validation,
    )
    result_file = args.results_dir / f"{args.baseline}.json"
    evaluation = evaluate_generator(
        args.baseline,
        generator,
        holdout,
        result_file=result_file,
        ledger=HoldoutLedger(args.ledger),
        initial_cost_usd=compile_cost,
        initial_latency_seconds=compile_latency,
    )
    print(
        f"{evaluation.name}: build={evaluation.build_rate:.1%}, "
        f"pass={evaluation.pass_rate:.1%}, "
        f"branch={evaluation.branch_coverage:.1%}, "
        f"cost=${evaluation.cost_usd:.4f}, "
        f"latency={evaluation.latency_seconds:.2f}s"
    )
    print(f"Saved locked result to {result_file.resolve()}")


def _report(args: argparse.Namespace) -> None:
    evaluations = [
        BaselineEvaluation.load(path)
        for path in sorted(args.results_dir.glob("*.json"))
    ]
    generate_report(evaluations, args.output)
    print(f"Saved final report to {args.output.resolve()}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and report the locked v-final evaluation"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Evaluate one baseline exactly once")
    run.add_argument("--baseline", choices=BASELINES, required=True)
    run.add_argument("--dataset", type=Path, required=True)
    run.add_argument("--source-root", type=Path, required=True)
    run.add_argument("--module-path", type=Path, required=True)
    run.add_argument("--results-dir", type=Path, default=Path("eval/v_final/results"))
    run.add_argument("--ledger", type=Path, default=Path("eval/v_final/ledger.json"))
    run.add_argument("--env-file", type=Path, default=Path(".env"))
    run.add_argument(
        "--allow-source-upload",
        action="store_true",
        help=(
            "Explicitly consent to sending focal source code, existing tests, "
            "and execution feedback to the configured external LLM provider. "
            "Not required for the CoverUp replay."
        ),
    )
    run.add_argument("--max-iters", type=int, default=4)
    run.add_argument("--bootstrap-train-size", type=int, default=10, choices=range(5, 11))
    run.add_argument(
        "--gepa-log-dir",
        type=Path,
        default=Path("eval/v_final/gepa_logs"),
    )
    coverup = run.add_mutually_exclusive_group()
    coverup.add_argument("--coverup-manifest", type=Path)
    coverup.add_argument("--coverup-tests-dir", type=Path)
    run.add_argument(
        "--coverup-cost-usd",
        type=float,
        default=0.0,
        help="Generation cost reported by the external CoverUp run.",
    )
    run.add_argument(
        "--coverup-generation-latency-seconds",
        type=float,
        default=0.0,
        help="Wall time of the external CoverUp generation run.",
    )
    run.set_defaults(handler=_run)

    report = subparsers.add_parser("report", help="Generate the final comparison")
    report.add_argument("results_dir", type=Path)
    report.add_argument("--output", type=Path, default=Path("eval/v_final/report.md"))
    report.set_defaults(handler=_report)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "run":
        if args.max_iters < 1:
            raise ValueError("--max-iters must be at least 1")
        _require_source_upload_consent(args)
        args.results_dir.mkdir(parents=True, exist_ok=True)
    args.handler(args)


if __name__ == "__main__":
    main()
