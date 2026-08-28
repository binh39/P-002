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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

from cloud.evaluation_dispatcher import RemoteEvaluationBackend
from cloud.run_job import _download_object, _upload_dir
from cloud.runtime_workspace import (
    _validate_project_id,
    detect_layout,
    find_project_root,
    safe_extract_runtime_bundle,
    safe_extract_zip,
)
from src.optimization.costs import aggregate_usage_events
from src.optimization.coveragepy import load_report, run_coverage
from src.optimization.models import ExperimentConfig, ProjectLayout, SymbolTarget
from src.optimization.runner import CoverUpExperimentRunner, _configure_runtime_environment, _test_environment


def _download_verified_runtime_object(
    bucket,
    object_name: str,
    destination: Path,
    *,
    expected_sha256: str,
    expected_generation: str | None = None,
) -> None:
    """Download a project runtime input and verify its immutable identity.

    Final-suite generation is a second execution path beside GEPA evaluation;
    it must enforce the same generation/checksum contract before extracting
    user source or a project virtual environment.
    """
    if expected_generation:
        blob = bucket.blob(object_name)
        try:
            blob.reload()
        except Exception as exc:  # noqa: BLE001 - surface an actionable identity error
            raise RuntimeError(f"Could not verify generation for runtime object {object_name}") from exc
        actual_generation = getattr(blob, "generation", None)
        if actual_generation is None or str(actual_generation) != str(expected_generation):
            raise RuntimeError(f"Runtime object generation changed: {object_name}")
    _download_object(bucket, object_name, destination)
    actual_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"Runtime object checksum changed: {object_name}")


def _artifact_index(
    artifacts: Path, generated_files: list[Path], source_files: list[Path] | None = None
) -> list[dict[str, object]]:
    """Describe browser-safe final-suite artifacts without exposing GCS object names."""
    records: list[dict[str, object]] = []
    candidates = [("generated_test", path, "text/x-python") for path in generated_files]
    candidates.extend(("source", path, "text/x-python") for path in source_files or [])
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


def _copy_source_artifacts(
    artifacts: Path,
    targets: list[SymbolTarget],
    config: ExperimentConfig,
    sample_repos: Path,
) -> list[Path]:
    """Copy selected source modules into the final artifact bundle for the browser viewer."""
    copied: list[Path] = []
    seen: set[tuple[str, str]] = set()
    for target in targets:
        normalized = target.source_file.replace("\\", "/")
        relative = PurePosixPath(normalized)
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            continue
        identity = (target.project, normalized)
        if identity in seen:
            continue
        seen.add(identity)
        package_dir = config.package_dir_for(target.project).resolve()
        roots = [package_dir.parent, package_dir]
        if target.project.startswith("sample:"):
            roots.insert(0, sample_repos / target.project.split(":", 1)[1])
        source_path = next(
            (
                candidate
                for root in roots
                if (candidate := (root / Path(*relative.parts)).resolve()).is_file()
                and (root.resolve() == candidate or root.resolve() in candidate.parents)
            ),
            None,
        )
        if source_path is None or source_path.stat().st_size > 1_000_000:
            continue
        safe_project = re.sub(r"[^A-Za-z0-9_.-]+", "_", target.project).strip("._-") or "project"
        destination = artifacts / "source" / safe_project / Path(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination)
        copied.append(destination)
    return copied


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
        not result.score or not result.score.get("valid") or result.score.get("tests_passed") is False
        for result in batch.results
    )
    statement = covered_statements / statement_denominator if statement_denominator else None
    branch = covered_branches / branch_denominator if branch_denominator else None
    score = (
        (statement + branch) / 2
        if statement is not None and branch is not None
        else statement
        if statement is not None
        else branch
    )
    return {
        "target_statement_coverage": statement,
        "target_branch_coverage": branch,
        "target_score": score,
        "target_covered_statements": covered_statements,
        "target_statement_count": statement_denominator,
        "target_covered_branches": covered_branches,
        "target_branch_count": branch_denominator,
        "target_count": len(batch.results),
        "completed_target_count": completed,
        "failed_target_count": failed,
    }


def _workspaces_for_targets(targets: list[SymbolTarget], tests_workspace: str) -> dict[str, Path]:
    """Resolve the persistent generated-test workspace for each selected project."""
    project_ids = {symbol_target.project for symbol_target in targets}
    root_workspace = Path(tests_workspace)
    if len(project_ids) == 1:
        return {project_id: root_workspace for project_id in project_ids}
    return {project_id: root_workspace / project_id for project_id in project_ids}


def _worker_jobs_from_environment() -> dict[str, str]:
    project = os.environ.get("PROMPTOPT_CLOUD_PROJECT", "").strip()
    region = os.environ.get("PROMPTOPT_CLOUD_REGION", "").strip()
    names = {
        "sample": os.environ.get("PROMPTOPT_EVALUATION_JOB_SAMPLE", "").strip(),
        "3.10": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY310", "").strip(),
        "3.11": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY311", "").strip(),
        "3.12": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY312", "").strip(),
        "3.13": os.environ.get("PROMPTOPT_EVALUATION_JOB_PY313", "").strip(),
    }
    relative_jobs = [name for name in names.values() if name and not name.startswith("projects/")]
    if relative_jobs and (not project or not region):
        raise RuntimeError(
            "Independent evaluation worker names require PROMPTOPT_CLOUD_PROJECT and PROMPTOPT_CLOUD_REGION"
        )
    return {
        version: (name if name.startswith("projects/") else f"projects/{project}/locations/{region}/jobs/{name}")
        for version, name in names.items()
        if name
    }


def _pin_sample_workers(manifest: dict, jobs: dict[str, str]) -> dict:
    pinned = json.loads(json.dumps(manifest))
    sample_job = jobs.get("sample", "")
    sample_image = os.environ.get("PROMPTOPT_SAMPLE_RUNTIME_IMAGE", "").strip()
    for project in pinned.get("projects", []):
        if project.get("kind") != "sample":
            continue
        if not sample_job or not sample_image:
            raise RuntimeError("Independent sample generation requires an immutable worker job and image")
        base_digest = str(project.get("runtime_digest") or f"sample:{project.get('sample_slug', project['project'])}")
        project["runtime_worker_job"] = sample_job
        project["runtime_image"] = sample_image
        project["execution_mode"] = project.get("execution_mode") or "generic_worker_bundle"
        project["runtime_digest"] = hashlib.sha256(
            json.dumps(
                {"sample": base_digest, "image": sample_image, "worker_job": sample_job},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    return pinned


def _safe_project_name(project: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", project).strip("._-") or "project"


def _copy_worker_artifacts(
    *,
    project: str,
    worker_root: Path,
    worker_result: dict,
    artifacts: Path,
) -> tuple[list[Path], list[Path]]:
    generated: list[Path] = []
    sources: list[Path] = []
    safe_project = _safe_project_name(project)
    for record in (worker_result.get("artifacts") or {}).get("files", []):
        relative = PurePosixPath(str(record.get("path") or ""))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"Worker {project} returned an unsafe artifact path")
        source = worker_root.joinpath(*relative.parts).resolve()
        if not source.is_file() or worker_root.resolve() not in source.parents:
            raise RuntimeError(f"Worker {project} omitted artifact {relative.as_posix()}")
        kind = str(record.get("kind") or "")
        if kind == "generated_test":
            suffix = relative.parts[1:] if relative.parts[0] == "generated_tests" else relative.parts
            destination = artifacts / "generated_tests" / safe_project / Path(*suffix)
            generated.append(destination)
        elif kind == "source":
            suffix = relative.parts[1:] if relative.parts[0] == "source" else relative.parts
            destination = artifacts / "source" / safe_project / Path(*suffix)
            sources.append(destination)
        elif kind == "coverage":
            destination = artifacts / "coverage" / f"{safe_project}-{relative.name}"
        else:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return generated, sources


def _merge_model_costs(results: list[dict]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for result in results:
        for model, values in ((result.get("cost_accounting") or {}).get("by_model") or {}).items():
            target = merged.setdefault(
                model,
                {
                    "estimated_cost_usd": 0.0,
                    "priced_request_count": 0,
                    "unpriced_request_count": 0,
                    "token_usage": {},
                },
            )
            target["estimated_cost_usd"] += float(values.get("estimated_cost_usd") or 0.0)
            target["priced_request_count"] += int(values.get("priced_request_count") or 0)
            target["unpriced_request_count"] += int(values.get("unpriced_request_count") or 0)
            for key, value in (values.get("token_usage") or {}).items():
                target["token_usage"][key] = int(target["token_usage"].get(key, 0)) + int(value)
    return merged


def _run_remote(
    args,
    artifacts: Path,
    scratch: Path,
    prompt_path: Path,
    targets: list[SymbolTarget],
    manifest: dict,
    jobs: dict[str, str],
) -> dict:
    manifest = _pin_sample_workers(manifest, jobs)
    placeholder = scratch / "remote-placeholder"
    placeholder.mkdir(parents=True, exist_ok=True)
    config = ExperimentConfig(
        project_root=placeholder,
        package_dir=placeholder,
        tests_dir=placeholder,
        artifacts_dir=artifacts,
        coverup_model=args.model,
        max_attempts=args.max_attempts,
        repeat_tests=args.repeat_tests,
        max_concurrency=args.max_concurrency,
        rate_limit=args.rate_limit,
        pytest_args=args.pytest_args,
    )
    backend = RemoteEvaluationBackend(
        bucket=args.bucket,
        artifact_prefix=args.artifacts_name.strip("/"),
        manifest=manifest,
        jobs=jobs,
        config=config,
        timeout_seconds=max(300, int(args.evaluation_worker_timeout_seconds)),
    )
    grouped: dict[str, list[SymbolTarget]] = {}
    for target in targets:
        grouped.setdefault(target.project, []).append(target)
    with ThreadPoolExecutor(max_workers=min(len(grouped), max(1, args.max_concurrency))) as pool:
        futures = {
            project: pool.submit(
                backend.generate_final_project,
                project,
                project_targets,
                prompt_path,
                seed=args.seed,
            )
            for project, project_targets in grouped.items()
        }
        worker_outputs = {project: future.result() for project, future in futures.items()}

    generated_files: list[Path] = []
    source_files: list[Path] = []
    worker_results: list[dict] = []
    per_project: dict[str, dict] = {}
    for project, output in sorted(worker_outputs.items()):
        worker_result = dict(output["result"])
        worker_results.append(worker_result)
        archive = scratch / "worker-results" / f"{_safe_project_name(project)}.zip"
        _download_object(args.bucket, output["artifact_object"], archive)
        extracted = scratch / "worker-results" / _safe_project_name(project)
        safe_extract_zip(archive, extracted)
        generated, sources = _copy_worker_artifacts(
            project=project,
            worker_root=extracted,
            worker_result=worker_result,
            artifacts=artifacts,
        )
        generated_files.extend(generated)
        source_files.extend(sources)
        project_metrics = dict((worker_result.get("projects") or {}).get(project) or {})
        project_metrics["runtime_digest"] = backend.projects[project].get("runtime_digest")
        per_project[project] = project_metrics

    metric_rows = [result.get("metrics") or {} for result in worker_results]
    covered_statements = sum(int(row.get("target_covered_statements") or 0) for row in metric_rows)
    statement_count = sum(int(row.get("target_statement_count") or 0) for row in metric_rows)
    covered_branches = sum(int(row.get("target_covered_branches") or 0) for row in metric_rows)
    branch_count = sum(int(row.get("target_branch_count") or 0) for row in metric_rows)
    statement = covered_statements / statement_count if statement_count else None
    branch = covered_branches / branch_count if branch_count else None
    score = (
        (statement + branch) / 2
        if statement is not None and branch is not None
        else statement
        if statement is not None
        else branch
    )
    project_statements = [
        value["project_statement_coverage"]
        for value in per_project.values()
        if value.get("project_statement_coverage") is not None
    ]
    project_branches = [
        value["project_branch_coverage"]
        for value in per_project.values()
        if value.get("project_branch_coverage") is not None
    ]
    token_usage: dict[str, int] = {}
    for result in worker_results:
        for key, value in (result.get("token_usage") or {}).items():
            token_usage[key] = token_usage.get(key, 0) + int(value)
    (artifacts / "generated_tests").mkdir(parents=True, exist_ok=True)
    shutil.make_archive(
        str(artifacts / "generated_tests"),
        "zip",
        root_dir=artifacts / "generated_tests",
    )
    artifact_files = _artifact_index(artifacts, generated_files, source_files)
    failed = sum(int(row.get("failed_target_count") or 0) for row in metric_rows)
    result = {
        "schema_version": 3,
        "status": "partial" if failed or any(row.get("status") == "partial" for row in worker_results) else "completed",
        "metrics": {
            "target_statement_coverage": statement,
            "target_branch_coverage": branch,
            "target_score": score,
            "target_covered_statements": covered_statements,
            "target_statement_count": statement_count,
            "target_covered_branches": covered_branches,
            "target_branch_count": branch_count,
            "target_count": sum(int(row.get("target_count") or 0) for row in metric_rows),
            "completed_target_count": sum(int(row.get("completed_target_count") or 0) for row in metric_rows),
            "failed_target_count": failed,
            "test_file_count": len(generated_files),
            "test_count": sum(int(row.get("test_count") or 0) for row in metric_rows),
            "project_statement_coverage": sum(project_statements) / len(project_statements)
            if project_statements
            else None,
            "project_branch_coverage": sum(project_branches) / len(project_branches) if project_branches else None,
        },
        "estimated_cost_usd": sum(float(result.get("estimated_cost_usd") or 0.0) for result in worker_results),
        "token_usage": token_usage,
        "cost_accounting": {
            "priced_request_count": sum(
                int((result.get("cost_accounting") or {}).get("priced_request_count") or 0) for result in worker_results
            ),
            "unpriced_request_count": sum(
                int((result.get("cost_accounting") or {}).get("unpriced_request_count") or 0)
                for result in worker_results
            ),
            "by_model": _merge_model_costs(worker_results),
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
    result["prompt_digest"] = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    result["runtime"] = {
        "projects": {
            name: {
                key: item.get(key)
                for key in (
                    "runtime_digest",
                    "runtime_protocol_version",
                    "execution_mode",
                    "runtime_image",
                    "runtime_worker_job",
                    "source_archive_sha256",
                    "runtime_bundle_sha256",
                )
                if item.get(key) is not None
            }
            for name, item in sorted(
                ((str(item["project"]), item) for item in manifest["projects"]),
                key=lambda pair: pair[0],
            )
        }
    }
    return result


def _stage_projects(args, root: Path, project_names: list[str] | None = None) -> tuple[Path, dict[str, ProjectLayout]]:
    """Return bundled sample root or an isolated uploaded-project layout map."""
    sample_repos = Path(args.sample_repos_dir).resolve()
    layouts: dict[str, ProjectLayout] = {}
    if not args.project_manifest_object:
        if not sample_repos.is_dir():
            raise RuntimeError(f"Bundled sample repository directory is missing: {sample_repos}")
        for project in project_names or []:
            repository_name = project.split(":", 1)[1] if project.startswith("sample:") else project
            repository_root = (sample_repos / repository_name).resolve()
            if not repository_root.is_dir() or sample_repos not in repository_root.parents:
                raise RuntimeError(f"Bundled sample repository is missing: {repository_name}")
            package_dir = repository_root / repository_name
            if not package_dir.is_dir():
                raise RuntimeError(f"Bundled sample repository has no package directory: {repository_name}")
            tests_dir = repository_root / "tests"
            layouts[project] = ProjectLayout(
                package_dir=package_dir,
                tests_dir=tests_dir,
                import_root=package_dir.parent,
            )
        return sample_repos, layouts

    manifest_path = root / "projects.json"
    _download_object(args.bucket, args.project_manifest_object, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    projects = manifest.get("projects", [])
    if not projects or manifest.get("schema_version") not in (2, 3):
        raise RuntimeError("Final generation requires an immutable-runtime manifest (schema 2 or 3)")
    staged_root = root / "sample_repos"
    for project in projects:
        name = str(project["project"])
        _validate_project_id(name)
        if project.get("kind") == "sample":
            slug = str(project.get("sample_slug") or name)
            repository_root = Path(args.sample_repos_dir).resolve() / slug
            if not repository_root.is_dir():
                raise RuntimeError(f"Bundled sample repository is missing: {slug}")
            destination = staged_root / name
            shutil.copytree(repository_root, destination)
            source, tests = detect_layout(
                destination,
                project.get("source_directory", slug),
                project.get("test_directory", "tests"),
            )
            layouts[name] = ProjectLayout(
                package_dir=source,
                tests_dir=tests,
                import_root=source.parent if (source / "__init__.py").is_file() else source,
            )
            continue
        required = (
            "archive_object",
            "runtime_bundle_object",
            "runtime_digest",
            "runtime_image",
            "runtime_worker_job",
            "source_archive_sha256",
            "runtime_bundle_sha256",
            "python_version",
        )
        missing_fields = [field for field in required if not project.get(field)]
        if missing_fields:
            raise RuntimeError(f"Uploaded project {name} has an incomplete immutable runtime: {missing_fields}")
        runtime_bundle = root / "runtimes" / f"{name}.tar.gz"
        _download_verified_runtime_object(
            args.bucket,
            project["runtime_bundle_object"],
            runtime_bundle,
            expected_sha256=str(project["runtime_bundle_sha256"]),
            expected_generation=project.get("runtime_bundle_generation"),
        )
        runtime_python = safe_extract_runtime_bundle(runtime_bundle, root / "runtimes" / name)
        archive = root / "archives" / f"{name}.zip"
        _download_verified_runtime_object(
            args.bucket,
            project["archive_object"],
            archive,
            expected_sha256=str(project["source_archive_sha256"]),
            expected_generation=project.get("source_archive_generation"),
        )
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
            python_executable=runtime_python,
            runtime_digest=str(project["runtime_digest"]),
        )
    return staged_root, layouts


def generate_local_project(
    *,
    artifacts: Path,
    prompt_path: Path,
    targets: list[SymbolTarget],
    config: ExperimentConfig,
    sample_repos: Path,
    seed: int,
) -> dict:
    """Generate and validate a final suite in the supplied runtime layout."""
    if not targets:
        raise ValueError("Final generation requires at least one target")
    os.environ["PYTHONHASHSEED"] = str(seed)
    batch = CoverUpExperimentRunner(config).evaluate_batch(
        targets,
        prompt_path,
        candidate_id="final",
        split="final",
        workspace_kind="candidate",
    )
    target_metrics = _target_metrics(batch)
    cost = aggregate_usage_events(
        event for result in batch.results for event in result.attempt_traces if isinstance(event, dict)
    )
    workspaces = _workspaces_for_targets(targets, batch.tests_workspace)
    per_project = {}
    suite_failed = False
    for project, workspace in sorted(workspaces.items()):
        project_layout = (
            config.projects[project]
            if config.projects and project in config.projects
            else ProjectLayout(
                package_dir=config.package_dir, tests_dir=config.tests_dir, import_root=config.package_dir.parent
            )
        )
        coverage_path = artifacts / "coverage" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', project)}.json"
        coverage_environment = _test_environment(
            config.project_root, (project_layout.import_root or project_layout.package_dir.parent,)
        )
        _configure_runtime_environment(coverage_environment, project_layout.python_executable)
        completed = run_coverage(
            project_root=config.project_root,
            package_dir=project_layout.package_dir,
            tests_dir=workspace,
            output=coverage_path,
            pytest_args=config.pytest_args,
            repeat_tests=config.repeat_tests,
            env=coverage_environment,
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
    project_statements = [
        value["project_statement_coverage"]
        for value in per_project.values()
        if value["project_statement_coverage"] is not None
    ]
    project_branches = [
        value["project_branch_coverage"]
        for value in per_project.values()
        if value["project_branch_coverage"] is not None
    ]
    generated_files = sorted(path for path in Path(batch.tests_workspace).rglob("test_*.py") if path.is_file())
    source_files = _copy_source_artifacts(artifacts, targets, config, sample_repos)
    archive_base = artifacts / "generated_tests"
    shutil.make_archive(str(archive_base), "zip", root_dir=Path(batch.tests_workspace))
    artifact_files = _artifact_index(artifacts, generated_files, source_files)
    status = "partial" if suite_failed or target_metrics["failed_target_count"] else "completed"
    return {
        "schema_version": 3,
        "status": status,
        "metrics": {
            **target_metrics,
            "test_file_count": len(generated_files),
            "test_count": _count_tests(generated_files),
            "project_statement_coverage": sum(project_statements) / len(project_statements)
            if project_statements
            else None,
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
    jobs = _worker_jobs_from_environment()
    if args.project_manifest_object:
        remote_manifest_path = scratch / "remote-projects.json"
        _download_object(args.bucket, args.project_manifest_object, remote_manifest_path)
        remote_manifest = json.loads(remote_manifest_path.read_text(encoding="utf-8"))
        if remote_manifest.get("schema_version") not in (2, 3) or not remote_manifest.get("projects"):
            raise RuntimeError("Final generation requires an immutable-runtime manifest (schema 2 or 3)")
        return _run_remote(
            args,
            artifacts,
            scratch,
            prompt_path,
            targets,
            remote_manifest,
            jobs,
        )
    project_names = sorted({str(target.project) for target in targets})
    sample_repos, layouts = _stage_projects(args, scratch, project_names)
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
    result = generate_local_project(
        artifacts=artifacts,
        prompt_path=prompt_path,
        targets=targets,
        config=config,
        sample_repos=sample_repos,
        seed=args.seed,
    )
    result["prompt_digest"] = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    return result


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
    parser.add_argument("--evaluation-worker-timeout-seconds", type=int, default=3600)
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
