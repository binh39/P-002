"""Minimal entry point embedded in project sandbox images."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from cloud.sandbox_builder import (
    EnvironmentArtifactBuilder,
    FileArtifactCache,
    ImageIdentity,
    RunnerIdentity,
    UvProjectResolver,
)
from cloud.sandbox_contract import RunSpec, SandboxSpec
from cloud.sandbox_dependency_plan import DependencyPlan
from cloud.sandbox_execution import clean_execution_workspace, execute_run

FORBIDDEN_MODULES = ("coverup", "dspy", "gepa", "google.cloud.aiplatform", "litellm", "openai")


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def image_contract() -> dict[str, object]:
    """Return machine-readable evidence that this is an isolated builder image."""

    forbidden_present = sorted(name for name in FORBIDDEN_MODULES if _module_available(name))
    return {
        "python_full_version": platform.python_version(),
        "python_minor": ".".join(platform.python_version().split(".")[:2]),
        "architecture": platform.machine().lower(),
        "uv_available": shutil.which("uv") is not None,
        "poetry_available": shutil.which("poetry") is not None,
        "managed_pytest_version": _package_version("pytest"),
        "managed_coverage_version": _package_version("coverage"),
        "forbidden_modules_present": forbidden_present,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project sandbox image agent")
    parser.add_argument("command", choices=("contract", "build", "run"))
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--cache-root", type=Path, default=Path("/cache"))
    parser.add_argument("--image-digest")
    parser.add_argument("--runner-profile", default="project_native")
    parser.add_argument("--pytest-version", default="sandbox-managed")
    parser.add_argument("--coverage-version", default="sandbox-managed")
    parser.add_argument("--sandbox-spec", type=Path)
    parser.add_argument("--run-spec", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--tests-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--workspace-root", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "contract":
        payload = image_contract()
        print(json.dumps(payload, sort_keys=True))
        return int(bool(payload["forbidden_modules_present"]))
    if arguments.command == "run":
        required = {
            "sandbox_spec": arguments.sandbox_spec,
            "run_spec": arguments.run_spec,
            "artifact": arguments.artifact,
            "manifest": arguments.manifest,
            "source_root": arguments.source_root,
            "tests_root": arguments.tests_root,
            "output_root": arguments.output_root,
            "workspace_root": arguments.workspace_root,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            parser.error(f"run requires: {', '.join('--' + name.replace('_', '-') for name in missing)}")
        spec = SandboxSpec.from_dict(json.loads(arguments.sandbox_spec.read_text(encoding="utf-8")))
        run_spec = RunSpec.from_dict(json.loads(arguments.run_spec.read_text(encoding="utf-8")))
        try:
            result = execute_run(
                spec,
                run_spec,
                manifest_path=arguments.manifest,
                archive_path=arguments.artifact,
                source_root=arguments.source_root,
                tests_root=arguments.tests_root,
                output_root=arguments.output_root,
                workspace_root=arguments.workspace_root,
            )
            print(json.dumps(result.as_dict(), sort_keys=True))
            return 0
        finally:
            clean_execution_workspace(arguments.workspace_root)
    if not arguments.project_root or not arguments.plan or not arguments.image_digest:
        parser.error("build requires --project-root, --plan and --image-digest")
    plan = DependencyPlan.from_dict(json.loads(arguments.plan.read_text(encoding="utf-8")))
    image = ImageIdentity.current(image_digest=arguments.image_digest)
    runner = RunnerIdentity(
        profile=arguments.runner_profile,
        pytest_version=arguments.pytest_version,
        coverage_version=arguments.coverage_version,
    )
    artifact = EnvironmentArtifactBuilder(
        FileArtifactCache(arguments.cache_root),
        UvProjectResolver(),
    ).build(arguments.project_root, plan, image, runner)
    print(
        json.dumps(
            {
                "fingerprint": artifact.manifest.fingerprint,
                "archive": str(artifact.archive),
                "artifact_sha256": artifact.manifest.artifact_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
