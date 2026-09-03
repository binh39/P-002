"""Exercise the development local-Docker runtime without API or LLM calls."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPOSITORY_ROOT / "app"
for import_root in (REPOSITORY_ROOT, APP_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from backend.infrastructure.storage import LocalObjectStorage  # noqa: E402
from backend.modules.projects.local_docker_runtime import LocalDockerRuntimePreparer  # noqa: E402
from backend.modules.projects.schemas import (  # noqa: E402
    ProjectRecord,
    ProjectSettings,
    ProjectStatus,
    RuntimeStatus,
)

from cloud.runtime_workspace import find_project_root, safe_extract_zip  # noqa: E402
from cloud.sandbox_builder import ArtifactManifest  # noqa: E402
from cloud.sandbox_contract import RunKind, SandboxStatus  # noqa: E402
from scripts.create_local_docker_upload_fixture import FILES  # noqa: E402
from src.optimization.models import SandboxEnvironment, SymbolTarget  # noqa: E402
from src.optimization.sandbox import OptimizerSandboxClient  # noqa: E402


def _fixture(path: Path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in FILES.items():
            archive.writestr(name, content)


async def _collect(runner: LocalDockerRuntimePreparer, prefix: str):
    for _ in range(1800):
        report = await runner.collect(prefix)
        if report is not None:
            return report
        await asyncio.sleep(1)
    raise TimeoutError("Local Docker integration did not finish within 30 minutes")


async def _run(image: str, *, exercise_cache_recovery: bool = False) -> dict[str, object]:
    data_root = REPOSITORY_ROOT / "app" / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    # Docker publishes a Linux venv containing a ``lib64`` symlink. Windows can
    # execute the acceptance run through Docker but may be unable to unlink that
    # symlink afterward, so cleanup is best-effort for this disposable harness.
    with tempfile.TemporaryDirectory(
        prefix="local-runtime-integration-",
        dir=data_root,
        ignore_cleanup_errors=True,
    ) as temporary:
        root = Path(temporary)
        storage = LocalObjectStorage(str(root / "storage"), "/api/v1")
        archive = root / "project.zip"
        _fixture(archive)
        object_name = "uploads/project.zip"
        await storage.put_local(object_name, archive.read_bytes())
        now = datetime.now(UTC)
        project = ProjectRecord(
            id="local-docker-integration",
            owner_id="local-user",
            name="Coverage conflict fixture",
            description="",
            upload_id="local-upload",
            object_name=object_name,
            branch="main",
            commit=None,
            status=ProjectStatus.READY,
            settings=ProjectSettings(),
            runtime_environment_id="local-environment",
            runtime_environment_name="Local Docker Python 3.12",
            created_at=now,
            updated_at=now,
        )
        runner = LocalDockerRuntimePreparer(
            storage=storage,
            image=image,
            root=root / "runtime",
        )
        if not await asyncio.to_thread(runner.is_healthy):
            raise RuntimeError(f"Docker image {image!r} did not pass its contract")
        prefix = await runner.start([project])
        report = await _collect(runner, prefix)
        payload = report.model_dump(mode="json")
        if report.status is not RuntimeStatus.READY:
            raise RuntimeError(json.dumps(payload, indent=2, sort_keys=True))

        fingerprint = report.environment_fingerprint or report.dependency_fingerprint
        if not fingerprint:
            raise RuntimeError("Admission report did not contain an environment fingerprint")
        artifact_root = runner.cache_root / "objects" / fingerprint
        manifest_path = artifact_root / "manifest.json"
        manifest = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        extracted = root / "optimizer-source"
        safe_extract_zip(archive, extracted)
        project_root = find_project_root(extracted)
        environment = SandboxEnvironment(
            image_digest=manifest.image.image_digest,
            artifact_archive=artifact_root / "environment.tar.gz",
            artifact_manifest=manifest_path,
            source_root=project_root,
            source_directory="src",
            requested_python="3.12",
            runner_profile=manifest.runner.profile,
        )
        target = SymbolTarget(
            "coverage-conflict-project",
            "src/demo/__init__.py",
            "classify",
            "validation",
        )
        generated_root = root / "generated"
        generated_root.mkdir()
        generated = generated_root / "test_candidate.py"
        generated.write_text(
            "from demo import classify\n\ndef test_candidate():\n    assert classify(-1) == 'other'\n",
            encoding="utf-8",
        )
        client = OptimizerSandboxClient({target.project: environment})
        baseline = client.evaluate(
            target,
            [project_root / "tests" / "test_demo.py"],
            project_tests=project_root / "tests",
            run_root=root / "baseline-run",
            run_id="ci-baseline",
            kind=RunKind.BASELINE,
        )
        candidate = client.evaluate(
            target,
            [generated],
            project_tests=project_root / "tests",
            run_root=root / "candidate-run",
            run_id="ci-candidate",
            kind=RunKind.CANDIDATE,
        )
        for name, evaluation in (("baseline", baseline), ("candidate", candidate)):
            if evaluation.result.status is not SandboxStatus.SUCCEEDED or evaluation.coverage is None:
                raise RuntimeError(
                    f"{name} sandbox evaluation failed: {evaluation.result.error_code}\n"
                    f"{evaluation.result.stderr}"
                )
            if evaluation.result.environment_fingerprint != fingerprint:
                raise RuntimeError(f"{name} result used a different environment fingerprint")

        cache_checks: dict[str, object] = {"enabled": exercise_cache_recovery}
        if exercise_cache_recovery:
            original_hash = manifest.artifact_sha256
            cache_hit = await _collect(runner, await runner.start([project]))
            if cache_hit.status is not RuntimeStatus.READY or cache_hit.environment_fingerprint != fingerprint:
                raise RuntimeError("Cache-hit admission did not reuse the same environment fingerprint")
            (artifact_root / "environment.tar.gz").write_bytes(b"intentionally-corrupt-ci-artifact")
            recovered = await _collect(runner, await runner.start([project]))
            recovered_manifest = ArtifactManifest.from_dict(
                json.loads((artifact_root / "manifest.json").read_text(encoding="utf-8"))
            )
            if recovered.status is not RuntimeStatus.READY or recovered_manifest.fingerprint != fingerprint:
                raise RuntimeError("Corrupt cache entry was not rebuilt atomically")
            recovered_hash = hashlib.sha256((artifact_root / "environment.tar.gz").read_bytes()).hexdigest()
            if recovered_hash != recovered_manifest.artifact_sha256:
                raise RuntimeError("Recovered cache artifact does not match its manifest")
            cache_checks.update(
                {
                    "cache_hit_fingerprint": cache_hit.environment_fingerprint,
                    "recovered_fingerprint": recovered.environment_fingerprint,
                    "original_artifact_sha256": original_hash,
                    "recovered_artifact_sha256": recovered_hash,
                    "quarantine_entries": len(tuple((runner.cache_root / "quarantine").iterdir())),
                }
            )

        return {
            "admission": payload,
            "baseline": baseline.result.as_dict(),
            "candidate": candidate.result.as_dict(),
            "cache": cache_checks,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="promptopt-sandbox:py3.12")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exercise-cache-recovery", action="store_true")
    args = parser.parse_args()
    serialized = json.dumps(
        asyncio.run(_run(args.image, exercise_cache_recovery=args.exercise_cache_recovery)),
        indent=2,
        sort_keys=True,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
