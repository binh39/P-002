from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.optimization.project_setup import prepare_project

SAMPLE_PROFILES = {
    "isort": ("isort", ("tomli",)),
    "mlxtend": (
        "mlxtend",
        ("numpy", "scipy", "pandas", "sklearn", "matplotlib", "joblib"),
    ),
    "typesystem": ("typesystem", ("jinja2", "yaml")),
}


@pytest.mark.parametrize("slug", SAMPLE_PROFILES)
def test_sample_project_setup_supplies_metadata_and_validates_imports(tmp_path: Path, slug: str):
    import_name, required = SAMPLE_PROFILES[slug]
    source = Path("src/sample_repo") / slug
    project = tmp_path / slug
    shutil.copytree(source, project, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    profile = project / ".promptopt" / "setup.json"
    profile.parent.mkdir()
    profile.write_text(
        json.dumps(
            {
                "distribution_name": slug,
                "import_name": import_name,
                "required_imports": required,
            }
        ),
        encoding="utf-8",
    )

    report, environment = prepare_project(project, project / import_name)

    assert report.distribution_name == slug
    assert report.import_validation == "passed"
    assert Path(report.metadata_directory, "METADATA").is_file()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib.metadata,sys; print(importlib.metadata.version(sys.argv[1]))",
            slug,
        ],
        cwd=project,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    assert completed.stdout.strip() == report.version


def test_project_setup_rejects_missing_dependency_before_model_execution(tmp_path: Path):
    project = tmp_path / "example"
    package = project / "example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    profile = project / ".promptopt" / "setup.json"
    profile.parent.mkdir()
    profile.write_text(
        json.dumps(
            {
                "distribution_name": "example",
                "import_name": "example",
                "required_imports": ["promptopt_dependency_that_does_not_exist"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Project environment preflight failed"):
        prepare_project(project, package)
