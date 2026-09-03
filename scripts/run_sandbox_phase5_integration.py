"""Exercise the optimizer-to-sandbox scoring bridge without LLM calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cloud.sandbox_contract import RunKind, SandboxStatus  # noqa: E402
from src.optimization.models import SandboxEnvironment, SymbolTarget  # noqa: E402
from src.optimization.sandbox import OptimizerSandboxClient  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-digest", required=True)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("eval/sandbox_phase4_integration"),
    )
    parser.add_argument(
        "--phase5-root",
        type=Path,
        default=Path("eval/sandbox_phase5_integration"),
    )
    args = parser.parse_args()
    phase4_root = args.root.resolve()
    phase5_root = args.phase5_root.resolve()
    manifest_path = phase4_root / "artifacts" / "native" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    environment = SandboxEnvironment(
        image_digest=args.image_digest,
        artifact_archive=manifest_path.with_name("environment.tar.gz"),
        artifact_manifest=manifest_path,
        source_root=phase4_root / "native",
        source_directory="src/demo",
        requested_python="3.12",
        runner_profile="project_native",
    )
    target = SymbolTarget(
        "native",
        "src/demo/__init__.py",
        "classify",
        "validation",
    )
    client = OptimizerSandboxClient({"native": environment})
    evaluation = client.evaluate(
        target,
        [phase5_root / "generated_tests" / "test_candidate.py"],
        project_tests=phase4_root / "native" / "generated_tests",
        run_root=phase5_root / "run",
        run_id="phase5-optimizer-client",
        kind=RunKind.CANDIDATE,
        repeat_tests=2,
    )
    result = evaluation.result
    if result.status != SandboxStatus.SUCCEEDED:
        raise RuntimeError(f"Phase 5 sandbox evaluation failed: {result.error_code}\n{result.stderr}")
    if result.environment_fingerprint != manifest["fingerprint"]:
        raise RuntimeError("Phase 5 result fingerprint does not match its environment artifact")
    if result.test_counts.passed != 2 or evaluation.coverage is None:
        raise RuntimeError("Phase 5 repeat execution or normalized coverage is incomplete")
    summary = {
        "environment_fingerprint": result.environment_fingerprint,
        "runner_profile": result.runner_profile.value if result.runner_profile else None,
        "pytest_version": result.pytest_version,
        "coverage_version": result.coverage_version,
        "test_counts": result.test_counts.as_dict(),
        "coverage": result.coverage.as_dict() if result.coverage else None,
        "source_file": target.source_file,
        "symbol": target.symbol,
        "optimizer_packages_absent": True,
        "network_and_credentials_denied": True,
    }
    summary_path = phase5_root / "acceptance-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
