"""Run the reproducible Phase 4 Docker sandbox acceptance checks.

This script consumes the fixtures and immutable environment artifacts under
``eval/sandbox_phase4_integration``.  It makes no network calls and executes
only the versioned RunSpec accepted by the sandbox agent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cloud.sandbox_contract import (  # noqa: E402 - support direct script execution
    CoverageMode,
    DependencyMode,
    DependencyPolicy,
    ResourceLimits,
    RunKind,
    RunnerProfile,
    RunSpec,
    SandboxSpec,
    SandboxStatus,
)
from cloud.sandbox_executor import DockerExecutionRequest, DockerSandboxExecutor  # noqa: E402


def _digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _execute(
    *,
    executor: DockerSandboxExecutor,
    image_digest: str,
    fixture_root: Path,
    artifact_root: Path,
    output_root: Path,
    run_id: str,
    runner_profile: RunnerProfile,
    source_file: str,
    symbol: str,
) -> dict[str, object]:
    manifest_path = artifact_root / "manifest.json"
    manifest = _load_manifest(manifest_path)
    fingerprint = str(manifest["fingerprint"])
    spec = SandboxSpec(
        project_id=f"phase4-{runner_profile.value}",
        archive_sha256=_digest_tree(fixture_root),
        requested_python="3.12",
        detected_python="3.12",
        source_directory="src",
        test_directory="generated_tests",
        dependency_policy=DependencyPolicy(
            mode=DependencyMode.MANIFEST,
            manifest="pyproject.toml",
            groups=("test",),
        ),
        runner_profile=runner_profile,
        coverage_mode=CoverageMode.STATEMENT_AND_BRANCH,
        allowed_environment_variables=("LANG", "LC_ALL", "PYTHONHASHSEED", "TZ"),
        resource_limits=ResourceLimits(
            cpu=1,
            memory_mb=512,
            timeout_seconds=60,
            maximum_processes=64,
            maximum_output_bytes=1024 * 1024,
            maximum_file_bytes=50 * 1024 * 1024,
        ),
    )
    run_spec = RunSpec(
        run_id=run_id,
        kind=RunKind.CANDIDATE,
        environment_fingerprint=fingerprint,
        test_paths=("generated_tests/test_generated.py",),
        source_file=source_file,
        symbol=symbol,
    )
    result = executor.execute(
        DockerExecutionRequest(
            image_digest=image_digest,
            artifact_archive=artifact_root / "environment.tar.gz",
            artifact_manifest=manifest_path,
            source_root=fixture_root,
            output_root=output_root,
            sandbox_spec=spec,
            run_spec=run_spec,
            environment={
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PYTHONHASHSEED": "0",
                "TZ": "UTC",
            },
        )
    )
    if result.status is not SandboxStatus.SUCCEEDED:
        raise RuntimeError(f"{run_id} failed: {result.error_code}\n{result.stderr}")
    if result.runner_profile is not runner_profile:
        raise RuntimeError(f"{run_id} selected {result.runner_profile}, expected {runner_profile}")
    if result.test_counts.collected < 1 or result.test_counts.failed:
        raise RuntimeError(f"{run_id} returned unexpected test counts: {result.test_counts}")
    if result.coverage is None or result.coverage.total_statements < 1:
        raise RuntimeError(f"{run_id} returned no measurable source coverage")
    if not result.coverage_artifact or not (output_root / result.coverage_artifact).is_file():
        raise RuntimeError(f"{run_id} did not publish its normalized coverage artifact")
    return result.as_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-digest", required=True)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("eval/sandbox_phase4_integration"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    executor = DockerSandboxExecutor()
    cases = (
        ("native", RunnerProfile.PROJECT_NATIVE, "src/demo/__init__.py", "classify"),
        ("managed", RunnerProfile.SANDBOX_MANAGED, "src/managed_demo/__init__.py", "multiply"),
    )
    results: dict[str, dict[str, object]] = {}
    for name, profile, source_file, symbol in cases:
        results[name] = _execute(
            executor=executor,
            image_digest=args.image_digest,
            fixture_root=root / name,
            artifact_root=root / "artifacts" / name,
            output_root=root / "results" / name,
            run_id=f"phase4-{name}",
            runner_profile=profile,
            source_file=source_file,
            symbol=symbol,
        )

    native_repeat = _execute(
        executor=executor,
        image_digest=args.image_digest,
        fixture_root=root / "native",
        artifact_root=root / "artifacts" / "native",
        output_root=root / "results" / "native-repeat",
        run_id="phase4-native-repeat",
        runner_profile=RunnerProfile.PROJECT_NATIVE,
        source_file="src/demo/__init__.py",
        symbol="classify",
    )
    for key in ("environment_fingerprint", "test_counts", "coverage", "runner_profile", "coverage_version"):
        if results["native"].get(key) != native_repeat.get(key):
            raise RuntimeError(f"native repeat differs in {key}")
    results["native_repeat"] = native_repeat

    summary_path = root / "results" / "acceptance-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, sort_keys=True))
    print(f"Phase 4 acceptance summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
