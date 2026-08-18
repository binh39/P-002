"""Execute one user-requested final test generation in an isolated Cloud Run Job.

Unlike ``cloud.run_job``, this command never invokes GEPA and never reads its
candidate workspaces.  Its only input is one immutable PromptSnapshot and the
target list selected by the user; its output is a browsable final test suite.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from cloud.run_job import _download_object, _upload_dir
from cloud.runtime_workspace import detect_layout, find_project_root, safe_extract_runtime_bundle, safe_extract_zip
from src.optimization.costs import aggregate_usage_events
from src.optimization.coveragepy import load_report, run_coverage
from src.optimization.models import ExperimentConfig, ProjectLayout, SymbolTarget
from src.optimization.runner import CoverUpExperimentRunner, _test_environment


def _artifact_index(artifacts: Path, generated_files: list[Path]) -> list[dict[str, object]]:
    """Describe browser-safe final-suite artifacts without exposing GCS object names."""
    records: list[dict[str, object]] = []
    candidates = [("generated_test", path, "text/x-python") for path in generated_files]
    candidates.extend(
        ("coverage", path, "application/json")
        for path in sorted((artifacts / "coverage").glob("*.json"))
        if path.is_file()
    )
    kind_counts: dict[str, int] = {}
    for kind, path, content_type in candidates:
        try:
            content = path.read_bytes()
            relative = path.resolve().relative_to(artifacts.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        records.append(
            {
                "id": f"{kind.replace('_', '-')}-{kind_counts[kind]}",
                "kind": kind,
                "path": relative,
                "content_type": content_type,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return records


def _count_tests(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        total += sum(
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_")
            for node in ast.walk(tree)
        )
    return total


def _project_totals(report: dict) -> tuple[float | None, float | None]:
    totals = report.get("totals") or {}
    statements = int(totals.get("num_statements", 0) or 0)
    branches = int(totals.get("num_branches", 0) or 0)
    statement = int(totals.get("covered_lines", 0) or 0) / statements if statements else None
    branch = int(totals.get("covered_branches", 0) or 0) / branches if branches else None
    return statement, branch


def _target_metrics(batch) -> dict:
    scores = [result.score for result in batch.results if result.score and result.score.get("valid")]
    statement_denominator = sum(int(score.get("num_statements", 0) or 0) for score in scores)
    branch_denominator = sum(int(score.get("num_branches", 0) or 0) for score in scores)
    covered_statements = sum(int(score.get("covered_statements", 0) or 0) for score in scores)
    covered_branches = sum(int(score.get("covered_branches", 0) or 0) for score in scores)
    completed = len(scores)
    failed = sum(
        not result.score
        or not result.score.get("valid")
        or result.score.get("tests_passed") is False
        for result in batch.results
    )
    statement = covered_statements / statement_denominator if statement_denominator else None
    branch = covered_branches / branch_denominator if branch_denominator else None
    score = (
        (statement + branch) / 2
        if statement is not None and branch is not None
        else statement if statement is not None else branch
    )
    return {
        "target_statement_coverage": statement,
        "target_branch_coverage": branch,
        "target_score": score,
        "target_count": len(batch.results),
        "completed_target_count": completed,
        "failed_target_count": failed,
    }


def _stage_projects(args, root: Path) -> tuple[Path, dict[str, ProjectLayout]]:
    """Return bundled sample root or an isolated uploaded-project layout map."""
    sample_repos = Path(args.sample_repos_dir).resolve()
    layouts: dict[str, ProjectLayout] = {}
    if not args.project_manifest_object:
        if not sample_repos.is_dir():
            raise RuntimeError(f"Bundled sample repository directory is missing: {sample_repos}")
        return sample_repos, layouts

    manifest_path = root / "projects.json"
    _download_object(args.bucket, args.project_manifest_object, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    projects = manifest.get("projects", [])
    if not projects or not manifest.get("runtime_bundle_object"):
        raise RuntimeError("Uploaded final generation requires projects and a prepared runtime bundle")
    runtime_bundle = root / "runtime.tar.gz"
    _download_object(args.bucket, manifest["runtime_bundle_object"], runtime_bundle)
    runtime_python = safe_extract_runtime_bundle(runtime_bundle, root / "runtime")
    os.environ["TESTGEN_PYTHON"] = str(runtime_python)
    staged_root = root / "sample_repos"
    for project in projects:
        name = str(project["project"])
        archive = root / "archives" / f"{name}.zip"
        _download_object(args.bucket, project["archive_object"], archive)
        extracted = root / "projects" / name
        safe_extract_zip(archive, extracted)
        project_root = find_project_root(extracted)
        source, tests = detect_layout(
            project_root,
            project.get("source_directory", "src"),
            project.get("test_directory", "tests"),
        )
        destination = staged_root / name
        shutil.copytree(project_root, destination)
        staged_source = destination / source.relative_to(project_root)
        staged_tests = destination / tests.relative_to(project_root)
        layouts[name] = ProjectLayout(
            package_dir=staged_source,
            tests_dir=staged_tests,
            import_root=staged_source.parent if (staged_source / "__init__.py").is_file() else staged_source,
        )
    return staged_root, layouts


def _run(args, artifacts: Path) -> dict:
    scratch = artifacts.parent / "inputs"
    scratch.mkdir(parents=True, exist_ok=True)
    prompt_path = scratch / "prompt.json"
    targets_path = scratch / "targets.json"
    _download_object(args.bucket, args.prompt_object, prompt_path)
    _download_object(args.bucket, args.targets_object, targets_path)
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
    if set(prompt) != {"initial", "error"} or not all(isinstance(value, str) for value in prompt.values()):
        raise RuntimeError("Prompt snapshot must contain only initial and error strings")
    raw_targets = json.loads(targets_path.read_text(encoding="utf-8"))
    if not isinstance(raw_targets, list) or not raw_targets:
        raise RuntimeError("Target manifest is empty")
    targets = [
        SymbolTarget(
            project=str(target["project"]),
            source_file=str(target["source_file"]),
            symbol=str(target["symbol"]),
            split="final",
        )
        for target in raw_targets
    ]
    sample_repos, layouts = _stage_projects(args, scratch)
    package_dir = sample_repos / "isort" / "isort"
    tests_dir = sample_repos / "isort" / "tests"
    if layouts:
        first = next(iter(layouts.values()))
        package_dir, tests_dir = first.package_dir, first.tests_dir
    config = ExperimentConfig(
        project_root=Path("/app"),
        package_dir=package_dir,
        tests_dir=tests_dir,
        artifacts_dir=artifacts,
        coverup_model=args.model,
        max_attempts=args.max_attempts,
        repeat_tests=args.repeat_tests,
        max_concurrency=args.max_concurrency,
        rate_limit=args.rate_limit,
        pytest_args=args.pytest_args,
        projects=layouts or None,
    )
    os.environ["PYTHONHASHSEED"] = str(args.seed)
    batch = CoverUpExperimentRunner(config).evaluate_batch(
        targets,
        prompt_path,
        candidate_id="final",
        split="final",
        workspace_kind="candidate",
    )
    target = _target_metrics(batch)
    cost = aggregate_usage_events(
        event
        for result in batch.results
        for event in result.attempt_traces
        if isinstance(event, dict)
    )
    workspaces = {target.project: Path(batch.tests_workspace)}
    if len({target.project for target in targets}) > 1:
        root_workspace = Path(batch.tests_workspace)
        workspaces = {project: root_workspace / project for project in {target.project for target in targets}}
    per_project = {}
    suite_failed = False
    for project, workspace in sorted(workspaces.items()):
        project_layout = config.projects[project] if config.projects and project in config.projects else ProjectLayout(
            package_dir=config.package_dir, tests_dir=config.tests_dir, import_root=config.package_dir.parent
        )
        coverage_path = artifacts / "coverage" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', project)}.json"
        completed = run_coverage(
            project_root=config.project_root,
            package_dir=project_layout.package_dir,
            tests_dir=workspace,
            output=coverage_path,
            pytest_args=config.pytest_args,
            repeat_tests=config.repeat_tests,
            env=_test_environment(config.project_root, (project_layout.import_root or project_layout.package_dir.parent,)),
        )
        if completed.returncode:
            suite_failed = True
        statement = branch = None
        if coverage_path.is_file():
            statement, branch = _project_totals(load_report(coverage_path))
        per_project[project] = {
            "pytest_exit_code": completed.returncode,
            "project_statement_coverage": statement,
            "project_branch_coverage": branch,
        }
    project_statements = [value["project_statement_coverage"] for value in per_project.values() if value["project_statement_coverage"] is not None]
    project_branches = [value["project_branch_coverage"] for value in per_project.values() if value["project_branch_coverage"] is not None]
    generated_files = sorted(path for path in Path(batch.tests_workspace).rglob("test_*.py") if path.is_file())
    archive_base = artifacts / "generated_tests"
    shutil.make_archive(str(archive_base), "zip", root_dir=Path(batch.tests_workspace))
    artifact_files = _artifact_index(artifacts, generated_files)
    status = "partial" if suite_failed or target["failed_target_count"] else "completed"
    return {
        "schema_version": 2,
        "status": status,
        "metrics": {
            **target,
            "test_file_count": len(generated_files),
            "test_count": _count_tests(generated_files),
            "project_statement_coverage": sum(project_statements) / len(project_statements) if project_statements else None,
            "project_branch_coverage": sum(project_branches) / len(project_branches) if project_branches else None,
        },
        "estimated_cost_usd": cost["estimated_cost_usd"],
        "token_usage": cost["token_usage"],
        "cost_accounting": {
            "priced_request_count": cost["priced_request_count"],
            "unpriced_request_count": cost["unpriced_request_count"],
            "by_model": cost["by_model"],
        },
        "projects": per_project,
        "generated_tests": [path.relative_to(artifacts).as_posix() for path in generated_files],
        "artifacts": {
            "manifest": "test_generation_result.json",
            "suite_zip": "generated_tests.zip",
            "generated_tests_directory": "generated_tests",
            "coverage_directory": "coverage",
            "files": artifact_files,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--artifacts-name", required=True)
    parser.add_argument("--prompt-object", required=True)
    parser.add_argument("--targets-object", required=True)
    parser.add_argument("--project-manifest-object")
    parser.add_argument("--sample-repos-dir", default="/app/sample_repo")
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--repeat-tests", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=5)
    parser.add_argument("--rate-limit", type=int)
    parser.add_argument("--pytest-args", default="")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.artifacts_name.strip("/").startswith("prompt_optimization_v3"):
        parser.error("Final test generation may not write to the protected prompt_optimization_v3 prefix")
    with tempfile.TemporaryDirectory(prefix="promptopt-final-tests-") as temporary:
        artifacts = Path(temporary) / "artifacts"
        artifacts.mkdir(parents=True)
        try:
            result = _run(args, artifacts)
            (artifacts / "test_generation_result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            job_result = {"status": "succeeded", "return_code": 0, "missing_artifacts": [], "error": None}
            exit_code = 0
        except Exception as exc:  # noqa: BLE001 - must always publish a terminal manifest
            detail = f"{type(exc).__name__}: {exc}"[-4000:]
            print(detail, file=sys.stderr, flush=True)
            job_result = {
                "status": "failed",
                "return_code": 1,
                "missing_artifacts": ["test_generation_result.json"],
                "error": detail,
            }
            exit_code = 1
        (artifacts / "job_result.json").write_text(json.dumps(job_result, indent=2), encoding="utf-8")
        _upload_dir(args.bucket, args.artifacts_name, artifacts)
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
