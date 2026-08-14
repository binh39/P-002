import json
from pathlib import Path

import pytest

from src.optimization.combined_suite import prepare_combined_tests


def _write_replicate(root: Path, candidate: str, workspace: Path) -> None:
    record = root / "runs" / candidate / "validation" / "run" / "record.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({
        "tests_workspace": str(workspace),
        "results": [{
            "target": {
                "project": "isort",
                "source_file": "isort/main.py",
                "symbol": "sort_imports",
                "split": "validation",
            }
        }],
    }), encoding="utf-8")


def test_prepare_combined_tests_renames_colliding_modules(tmp_path):
    artifacts = tmp_path / "artifacts"
    for index in range(2):
        workspace = artifacts / "generated_tests" / f"candidate-{index}"
        workspace.mkdir(parents=True)
        (workspace / "test_opt_1.py").write_text(
            f"def test_{index}(): pass\n", encoding="utf-8"
        )
        _write_replicate(artifacts, f"candidate-{index}", workspace)

    tests_root, targets, counts = prepare_combined_tests(
        artifacts, tmp_path / "combined"
    )

    copied = sorted((tests_root / "isort").glob("test_*.py"))
    assert len(copied) == 2
    assert copied[0].name != copied[1].name
    assert counts == {"isort": 2}
    assert targets[0].symbol == "sort_imports"


def test_prepare_combined_tests_refuses_to_overwrite_existing_output(tmp_path):
    artifacts = tmp_path / "artifacts"
    for index in range(2):
        workspace = artifacts / "generated_tests" / f"candidate-{index}"
        workspace.mkdir(parents=True)
        (workspace / "test_opt_1.py").write_text("def test_ok(): pass\n", encoding="utf-8")
        _write_replicate(artifacts, f"candidate-{index}", workspace)
    output = tmp_path / "combined"
    output.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        prepare_combined_tests(artifacts, output)
