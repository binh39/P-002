"""Exercise the Phase 0 sandbox runner profiles in disposable workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from cloud.sandbox_runner_profiles import select_runner_profile


def package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def write_fixture(root: Path) -> None:
    (root / "src" / "demo").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "demo" / "__init__.py").write_text(
        "def add(left, right):\n    return left + right\n", encoding="utf-8"
    )
    (root / "pytest.ini").write_text(
        "[pytest]\nmarkers = sandbox: sandbox runner spike\n", encoding="utf-8"
    )
    (root / "tests" / "conftest.py").write_text(
        "def pytest_configure(config):\n    config._sandbox_spike_plugin_loaded = True\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_profiles.py").write_text(
        "import asyncio\n"
        "import sqlite3\n"
        "import pytest\n"
        "from demo import add\n\n"
        "@pytest.mark.sandbox\n"
        "def test_custom_marker_conftest_and_native_extension(pytestconfig):\n"
        "    assert pytestconfig._sandbox_spike_plugin_loaded\n"
        "    assert sqlite3.connect(':memory:').execute('select 1').fetchone() == (1,)\n"
        "    assert add(2, 3) == 5\n\n"
        "def test_async_behavior():\n"
        "    async def compute():\n"
        "        await asyncio.sleep(0)\n"
        "        return 7\n"
        "    assert asyncio.run(compute()) == 7\n",
        encoding="utf-8",
    )
    (root / ".sandbox-coveragerc").write_text(
        "[run]\nbranch = True\nsource = src/demo\n[report]\nfail_under = 0\n",
        encoding="utf-8",
    )


def run_profile(profile: str) -> dict[str, object]:
    inventory = {
        name: found
        for name in ("pytest", "coverage")
        if (found := package_version(name)) is not None
    }
    if profile == "fallback":
        decision = select_runner_profile({"pytest": inventory.get("pytest", "8.4.2")})
        if decision.error_code != "INCOMPLETE_PROJECT_RUNNER":
            raise RuntimeError(f"Unexpected fallback decision: {decision}")
        return {
            "profile": profile,
            "status": "passed",
            "decision": decision.profile.value,
            "error_code": decision.error_code,
        }

    if "pytest" not in inventory or "coverage" not in inventory:
        raise RuntimeError("The native and managed spike profiles require pytest and coverage on PYTHONPATH")

    selected_inventory = inventory if profile == "native" else {}
    before = hashlib.sha256(json.dumps(selected_inventory, sort_keys=True).encode()).hexdigest()
    decision = select_runner_profile(selected_inventory)
    expected = "project_native" if profile == "native" else "sandbox_managed"
    if decision.profile.value != expected:
        raise RuntimeError(f"Expected {expected}, got {decision.profile.value}: {decision.reason}")

    with tempfile.TemporaryDirectory(prefix=f"sandbox-{profile}-spike-") as temporary:
        root = Path(temporary)
        write_fixture(root)
        environment = os.environ.copy()
        source_path = str(root / "src")
        environment["PYTHONPATH"] = os.pathsep.join(
            item for item in (source_path, environment.get("PYTHONPATH", "")) if item
        )
        coverage_json = root / "coverage.json"
        commands = [
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                f"--rcfile={root / '.sandbox-coveragerc'}",
                "-m",
                "pytest",
                "-q",
                str(root / "tests"),
            ],
            [
                sys.executable,
                "-m",
                "coverage",
                "json",
                f"--rcfile={root / '.sandbox-coveragerc'}",
                "-o",
                str(coverage_json),
            ],
        ]
        outputs = []
        for command in commands:
            completed = subprocess.run(
                command,
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            outputs.append(completed.stdout + completed.stderr)
            if completed.returncode != 0:
                raise RuntimeError(f"Spike command failed ({completed.returncode}): {' '.join(command)}\n{outputs[-1]}")
        totals = json.loads(coverage_json.read_text(encoding="utf-8"))["totals"]

    after = hashlib.sha256(json.dumps(selected_inventory, sort_keys=True).encode()).hexdigest()
    if before != after:
        raise RuntimeError("Runner selection mutated the project package inventory")
    return {
        "profile": profile,
        "status": "passed",
        "decision": decision.profile.value,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "pytest": inventory["pytest"],
        "coverage": inventory["coverage"],
        "tests": 2,
        "covered_statements": totals["covered_lines"],
        "total_statements": totals["num_statements"],
        "inventory_unchanged": before == after,
        "capabilities": ["custom_marker", "conftest", "native_extension", "asyncio"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("native", "managed", "fallback"), required=True)
    args = parser.parse_args()
    print(json.dumps(run_profile(args.profile), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
