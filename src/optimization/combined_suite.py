from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from .coveragepy import load_report, run_coverage, symbol_coverage
from .metrics import aggregate_coverage_score, score_symbol
from .models import SymbolTarget
from .runner import _test_environment, _zero_coverage_like


def _load_records(artifacts_dir: Path) -> list[dict[str, Any]]:
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(artifacts_dir.glob("runs/**/record.json"))
    ]
    if len(records) < 2:
        raise ValueError("Combined-suite verification requires at least two replicates")
    return records


def _resolve_workspace(artifacts_dir: Path, configured: str) -> Path:
    workspace = Path(configured)
    if workspace.is_dir():
        return workspace.resolve()
    matches = list(
        artifacts_dir.glob(f"generated_tests/**/{workspace.name}")
    )
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Cannot resolve generated-test workspace {configured!r} under {artifacts_dir}"
        )
    return matches[0].resolve()


def prepare_combined_tests(
    artifacts_dir: Path,
    output_dir: Path,
) -> tuple[Path, list[SymbolTarget], dict[str, int]]:
    """Copy every replicate's saved tests into collision-free project suites."""
    records = _load_records(artifacts_dir)
    first_targets = [
        SymbolTarget.from_dict(result["target"])
        for result in records[0].get("results", [])
    ]
    expected = {
        (target.project, target.source_file, target.symbol, target.split)
        for target in first_targets
    }
    if not expected:
        raise ValueError("The first replicate has no target results")
    for record in records[1:]:
        actual = {
            (
                result["target"]["project"],
                result["target"]["source_file"],
                result["target"]["symbol"],
                result["target"].get("split", "train"),
            )
            for result in record.get("results", [])
        }
        if actual != expected:
            raise ValueError("Replicate target sets differ")

    tests_root = output_dir / "tests"
    if output_dir.exists():
        raise FileExistsError(
            f"Combined-suite output already exists: {output_dir}. Choose a new path."
        )
    tests_root.mkdir(parents=True)
    projects = sorted({target.project for target in first_targets})
    copied_counts = {project: 0 for project in projects}
    for replicate, record in enumerate(records):
        workspace = _resolve_workspace(
            artifacts_dir, str(record.get("tests_workspace", ""))
        )
        for project in projects:
            source_dir = workspace / project if len(projects) > 1 else workspace
            if not source_dir.is_dir():
                raise FileNotFoundError(
                    f"Generated tests for project {project!r} are missing in {workspace}"
                )
            destination_dir = tests_root / project
            destination_dir.mkdir(parents=True, exist_ok=True)
            for index, source in enumerate(sorted(source_dir.rglob("test_*.py"))):
                destination = (
                    destination_dir
                    / f"test_r{replicate:03d}_{index:04d}_{source.stem}.py"
                )
                shutil.copyfile(source, destination)
                copied_counts[project] += 1
    return tests_root, first_targets, copied_counts


def verify_combined_suite(
    *,
    project_root: Path,
    artifacts_dir: Path,
    output_dir: Path,
    sample_repos_dir: Path,
    pytest_args: str = "",
) -> dict[str, Any]:
    """Run the real union suites; only passing projects contribute verified scores."""
    project_root = project_root.resolve()
    artifacts_dir = artifacts_dir.resolve()
    output_dir = output_dir.resolve()
    tests_root, targets, copied_counts = prepare_combined_tests(
        artifacts_dir, output_dir
    )
    grouped: dict[str, list[SymbolTarget]] = {}
    for target in targets:
        grouped.setdefault(target.project, []).append(target)
    package_dirs = {
        project: (sample_repos_dir / project / project).resolve()
        for project in grouped
    }
    missing = [str(path) for path in package_dirs.values() if not path.is_dir()]
    if missing:
        raise FileNotFoundError("Missing sample package directories: " + ", ".join(missing))
    environment = _test_environment(
        project_root,
        tuple(sorted({path.parent for path in package_dirs.values()})),
    )
    project_reports = []
    verified_results = []
    for project in sorted(grouped):
        coverage_path = output_dir / f"coverage_{project}.json"
        completed = run_coverage(
            project_root=project_root,
            package_dir=package_dirs[project],
            tests_dir=tests_root / project,
            output=coverage_path,
            pytest_basetemp=output_dir / "pytest_tmp" / project,
            pytest_args=pytest_args,
            repeat_tests=0,
            env=environment,
        )
        project_report: dict[str, Any] = {
            "project": project,
            "status": "passed" if completed.returncode == 0 else "failed",
            "pytest_exit_code": completed.returncode,
            "copied_tests": copied_counts[project],
            "stdout": completed.stdout[-12000:],
            "coverage_file": str(coverage_path),
            "results": [],
        }
        if completed.returncode == 0 and coverage_path.is_file():
            coverage = load_report(coverage_path)
            for target in grouped[project]:
                try:
                    measured = symbol_coverage(
                        coverage, target.source_file, target.symbol
                    )
                except KeyError as exc:
                    project_report["status"] = "failed"
                    project_report["results"].append({
                        "target": target.__dict__,
                        "error": str(exc),
                    })
                    continue
                score = score_symbol(_zero_coverage_like(measured), measured).as_dict()
                result = {"target": target.__dict__, "score": score}
                project_report["results"].append(result)
                verified_results.append(result)
        project_reports.append(project_report)

    verified = all(report["status"] == "passed" for report in project_reports)
    report = {
        "schema_version": 1,
        "verified": verified,
        "meaning": (
            "All copied tests passed together and coverage was measured"
            if verified
            else "At least one project suite failed; union coverage is not verified"
        ),
        "replicate_count": len(_load_records(artifacts_dir)),
        "target_count": len(targets),
        "copied_tests": copied_counts,
        "projects": project_reports,
        "aggregate": (
            aggregate_coverage_score(verified_results) if verified else None
        ),
    }
    (output_dir / "combined_suite_verification.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the union of generated tests from repeated runs"
    )
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--sample-repos-dir", type=Path, default=Path("src/sample_repo")
    )
    parser.add_argument("--pytest-args", default="")
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    sample_repos = args.sample_repos_dir
    if not sample_repos.is_absolute():
        sample_repos = project_root / sample_repos
    report = verify_combined_suite(
        project_root=project_root,
        artifacts_dir=args.artifacts,
        output_dir=args.output_dir,
        sample_repos_dir=sample_repos,
        pytest_args=args.pytest_args,
    )
    print(json.dumps({
        "verified": report["verified"],
        "aggregate": report["aggregate"],
        "projects": [
            {
                "project": item["project"],
                "status": item["status"],
                "pytest_exit_code": item["pytest_exit_code"],
                "copied_tests": item["copied_tests"],
            }
            for item in report["projects"]
        ],
    }, indent=2))
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
