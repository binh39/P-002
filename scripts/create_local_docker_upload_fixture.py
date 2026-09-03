"""Create a tiny ZIP for visually validating local Docker project admission."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

FILES = {
    "coverage-conflict-project/pyproject.toml": """
[project]
name = "coverage-conflict-project"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
test = ["pytest==9.1.1", "coverage==7.10.7"]

[tool.pytest.ini_options]
markers = ["sandbox: local Docker admission"]
""".lstrip(),
    "coverage-conflict-project/src/demo/__init__.py": """def classify(value):
    if value > 0:
        return "positive"
    return "other"
""",
    "coverage-conflict-project/tests/conftest.py": """import pytest


@pytest.fixture
def positive_value():
    return 2
""",
    "coverage-conflict-project/tests/test_demo.py": """import importlib.util
import os
import socket

import pytest

from demo import classify


@pytest.mark.sandbox
def test_project_uses_its_own_coverage_tooling(positive_value):
    assert classify(positive_value) == "positive"
    assert importlib.util.find_spec("gepa") is None
    assert importlib.util.find_spec("coverup") is None
    assert not any(name.startswith(("AWS_", "GOOGLE_", "AZURE_")) for name in os.environ)
    with pytest.raises(OSError):
        socket.create_connection(("1.1.1.1", 53), timeout=1)
""",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("app/data/coverage-conflict-project.zip"),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in FILES.items():
            archive.writestr(name, content)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
