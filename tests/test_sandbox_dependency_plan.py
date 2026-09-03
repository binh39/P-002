import json
import shutil
from pathlib import Path, PurePosixPath

import pytest

from cloud.runtime_workspace import RUNTIME_TOOL_PACKAGES
from cloud.sandbox_dependency_plan import (
    DependencyPlanError,
    DependencySelection,
    DependencySource,
    InstallTarget,
    build_dependency_plan,
)
from cloud.sandbox_metadata import ProjectMetadataError, resolve_python_metadata

CATALOG = json.loads((Path(__file__).parent / "fixtures" / "sandbox_projects.json").read_text(encoding="utf-8"))


def materialize(case_name: str, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in CATALOG[case_name]["files"].items():
        destination = root / PurePosixPath(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return root


def test_python_metadata_reads_pep621_and_uv_lock_sources(tmp_path):
    root = materialize("uv_locked", tmp_path / "project")

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.12"
    assert resolution.inferred is False
    assert [(source.path, source.field) for source in resolution.sources] == [
        ("pyproject.toml", "[project].requires-python"),
        ("uv.lock", "requires-python"),
    ]


def test_python_metadata_can_be_resolved_from_lock_only(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "uv.lock").write_text('version = 1\nrequires-python = ">=3.13"\n', encoding="utf-8")

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.13"
    assert resolution.sources[0].path == "uv.lock"


def test_python_metadata_supports_poetry_constraint(tmp_path):
    root = materialize("poetry_locked", tmp_path / "project")

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.12"
    assert resolution.sources[0].field == "[tool.poetry.dependencies].python"
    assert resolution.sources[0].specifier == ">=3.12,<4.0"


@pytest.mark.parametrize("case_name, source_path", [("setup_cfg_only", "setup.cfg"), ("setup_py_only", "setup.py")])
def test_python_metadata_supports_static_setup_files_without_execution(tmp_path, case_name, source_path):
    root = materialize(case_name, tmp_path / case_name)

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.12"
    assert resolution.sources[0].path == source_path
    assert not (root / "SETUP_EXECUTED").exists()


def test_python_version_hints_are_used_after_authoritative_metadata(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "hints"\nversion = "1"\nrequires-python = ">=3.10"\n',
        encoding="utf-8",
    )
    (root / ".python-version").write_text("3.11.9\n", encoding="utf-8")
    (root / "runtime.txt").write_text("python-3.11.8\n", encoding="utf-8")

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.11"
    assert [source.path for source in resolution.sources] == [
        "pyproject.toml",
        ".python-version",
        "runtime.txt",
    ]
    assert [source.priority for source in resolution.sources] == [10, 70, 80]


def test_conflicting_python_metadata_reports_every_source(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "conflict"\nversion = "1"\nrequires-python = ">=3.12"\n',
        encoding="utf-8",
    )
    (root / ".python-version").write_text("3.11\n", encoding="utf-8")

    with pytest.raises(ProjectMetadataError) as captured:
        resolve_python_metadata(root)

    assert captured.value.error_code == "CONFLICTING_PYTHON_METADATA"
    assert captured.value.sources == ("pyproject.toml", ".python-version")
    assert "pyproject.toml:[project].requires-python" in str(captured.value)
    assert ".python-version:python version hint" in str(captured.value)


def test_missing_python_metadata_defaults_to_312_and_is_marked_inferred(tmp_path):
    root = materialize("no_tests", tmp_path / "project")

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.12"
    assert resolution.combined_specifier == "==3.12.*"
    assert resolution.inferred is True
    assert resolution.sources == ()


def test_exact_python_patch_above_old_sampling_range_is_supported(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "exact-patch"\nversion = "1"\nrequires-python = "==3.12.50"\n',
        encoding="utf-8",
    )

    resolution = resolve_python_metadata(root)

    assert resolution.python_version == "3.12"


@pytest.mark.parametrize(
    "case_name, expected_source, expected_manifest, expected_lock",
    [
        ("uv_locked", DependencySource.UV_LOCK, "pyproject.toml", "uv.lock"),
        ("poetry_locked", DependencySource.POETRY_LOCK, "pyproject.toml", "poetry.lock"),
        ("conflict_v1", DependencySource.REQUIREMENTS, "requirements.txt", None),
        ("no_runner", DependencySource.PYPROJECT, "pyproject.toml", None),
        ("setup_cfg_only", DependencySource.SETUP_CFG, "setup.cfg", None),
        ("setup_py_only", DependencySource.SETUP_PY, "setup.py", None),
        ("no_tests", DependencySource.NONE, None, None),
    ],
)
def test_dependency_source_priority(case_name, expected_source, expected_manifest, expected_lock, tmp_path):
    root = materialize(case_name, tmp_path / case_name)

    plan = build_dependency_plan(root)

    assert plan.source == expected_source
    assert plan.manifest == expected_manifest
    assert plan.lock_file == expected_lock


def test_higher_priority_requirements_does_not_accumulate_other_requirement_files(tmp_path):
    root = materialize("conflict_v1", tmp_path / "project")
    (root / "requirements-dev.txt").write_text("dev-only==1\n", encoding="utf-8")
    (root / "requirements-test.txt").write_text("test-only==1\n", encoding="utf-8")

    plan = build_dependency_plan(root)

    assert plan.manifest == "requirements.txt"
    assert plan.declared_requirements == ("shared-dependency==1.0.0",)
    assert [path for path, _ in plan.input_digests] == ["requirements.txt"]


def test_safe_test_group_is_selected_without_all_groups_or_extras(tmp_path):
    root = materialize("conflicting_optional_groups", tmp_path / "project")

    plan = build_dependency_plan(root)

    assert plan.groups == ("test",)
    assert plan.extras == ()
    assert "shared-dependency==1.0.0" not in plan.declared_requirements
    assert "shared-dependency==2.0.0" not in plan.declared_requirements
    assert "shared-dependency==3.0.0" not in plan.declared_requirements
    assert "all-groups" not in json.dumps(plan.canonical_dict())
    assert "all-extras" not in json.dumps(plan.canonical_dict())


def test_explicit_group_and_extra_are_validated_and_included(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "selection"\n'
        'version = "1"\n'
        'dependencies = ["base==1"]\n\n'
        "[project.optional-dependencies]\n"
        'speed = ["fast==2"]\n\n'
        "[dependency-groups]\n"
        'test = ["pytest==9"]\n'
        'dev = ["dev-only==3"]\n',
        encoding="utf-8",
    )

    plan = build_dependency_plan(
        root,
        DependencySelection(groups=("dev",), extras=("speed",), package_index_refs=("pypi-public",)),
    )

    assert plan.groups == ("dev",)
    assert plan.extras == ("speed",)
    assert plan.package_index_refs == ("pypi-public",)
    assert plan.declared_requirements == ("base==1", "dev-only==3", "fast==2")


def test_group_and_extra_order_is_canonicalized_for_fingerprint(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "canonical-selection"\n'
        'version = "1"\n\n'
        "[project.optional-dependencies]\n"
        'alpha = ["alpha==1"]\n'
        'beta = ["beta==1"]\n\n'
        "[dependency-groups]\n"
        "test = []\n"
        'lint = ["lint==1"]\n',
        encoding="utf-8",
    )

    first = build_dependency_plan(root, DependencySelection(groups=("lint", "test"), extras=("beta", "alpha")))
    second = build_dependency_plan(root, DependencySelection(groups=("test", "lint"), extras=("alpha", "beta")))

    assert first.groups == ("lint", "test")
    assert first.extras == ("alpha", "beta")
    assert first.fingerprint == second.fingerprint


def test_poetry_caret_dependency_is_normalized_to_pep440(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[tool.poetry]\n"
        'name = "poetry-dependency"\n'
        'version = "1"\n\n'
        "[tool.poetry.dependencies]\n"
        'python = "^3.12"\n'
        'requests = "^2.31"\n',
        encoding="utf-8",
    )

    plan = build_dependency_plan(root)

    assert plan.declared_requirements == ("requests>=2.31,<3.0",)


def test_project_coverage_pin_is_not_replaced_by_optimizer_packages(tmp_path):
    root = materialize("coverage_7_10_7", tmp_path / "project")

    plan = build_dependency_plan(root)

    assert "coverage==7.10.7" in plan.declared_requirements
    assert "coverage==7.15.2" not in plan.declared_requirements
    assert "slipcover==1.0.18" not in plan.declared_requirements
    assert set(plan.declared_requirements) - {"pytest==9.1.1", "coverage==7.10.7"} == set()
    assert set(RUNTIME_TOOL_PACKAGES) - set(plan.declared_requirements)


def test_dependency_selection_has_no_arbitrary_install_command():
    with pytest.raises(TypeError, match="install_command"):
        DependencySelection(install_command="pip install attacker")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "reference",
    [
        "https://user:secret@example.invalid/simple",
        "user:secret@example",
        "../private-index",
        "TOKEN=value",
    ],
)
def test_package_index_must_be_a_credential_free_reference(tmp_path, reference):
    root = materialize("no_tests", tmp_path / "project")

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root, DependencySelection(package_index_refs=(reference,)))

    assert captured.value.error_code == "INVALID_PACKAGE_INDEX_REFERENCE"
    assert captured.value.sources == (reference,)


def test_same_content_in_different_roots_has_same_fingerprint(tmp_path):
    first = materialize("uv_locked", tmp_path / "first")
    second = materialize("uv_locked", tmp_path / "second")

    first_plan = build_dependency_plan(first)
    second_plan = build_dependency_plan(second)

    assert first_plan.fingerprint == second_plan.fingerprint
    assert first_plan.canonical_dict() == second_plan.canonical_dict()


def test_lock_group_python_and_install_target_changes_change_fingerprint(tmp_path):
    baseline_root = materialize("uv_locked", tmp_path / "baseline")
    lock_root = materialize("uv_locked", tmp_path / "lock")
    group_root = materialize("conflicting_optional_groups", tmp_path / "groups")
    python_root = materialize("no_tests", tmp_path / "python")
    target_root = materialize("uv_locked", tmp_path / "target")
    (lock_root / "uv.lock").write_text(
        (lock_root / "uv.lock").read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8"
    )
    (python_root / ".python-version").write_text("3.13\n", encoding="utf-8")

    baseline = build_dependency_plan(baseline_root)
    lock_changed = build_dependency_plan(lock_root)
    group_changed = build_dependency_plan(group_root, DependencySelection(groups=("dev",)))
    group_default = build_dependency_plan(group_root)
    python_changed = build_dependency_plan(python_root)
    target_changed = build_dependency_plan(
        target_root,
        DependencySelection(install_target=InstallTarget.PROJECT),
    )

    assert lock_changed.fingerprint != baseline.fingerprint
    assert group_changed.fingerprint != group_default.fingerprint
    assert python_changed.python.python_version == "3.13"
    assert (
        python_changed.fingerprint
        != build_dependency_plan(materialize("no_tests", tmp_path / "python-default")).fingerprint
    )
    assert target_changed.fingerprint != baseline.fingerprint


def test_invalid_high_priority_lock_does_not_fall_back_to_requirements(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "bad-lock"\nversion = "1"\n', encoding="utf-8")
    (root / "uv.lock").write_text("not valid [ toml", encoding="utf-8")
    (root / "requirements.txt").write_text("fallback-must-not-run==1\n", encoding="utf-8")

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root)

    assert captured.value.error_code in {"INVALID_TOML", "INVALID_DEPENDENCY_METADATA"}
    assert "uv.lock" in captured.value.sources


def test_metadata_error_contains_file_and_field_source(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "invalid"\nversion = "1"\nrequires-python = "not-a-specifier"\n',
        encoding="utf-8",
    )

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root)

    assert captured.value.error_code == "INVALID_PYTHON_REQUIREMENT"
    assert captured.value.sources == ("pyproject.toml",)
    assert "[project].requires-python" in str(captured.value)


def test_setup_py_dynamic_dependencies_are_rejected_without_execution(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "setup.py").write_text(
        "from pathlib import Path\n"
        "from setuptools import setup\n"
        "deps = ['dynamic==1']\n"
        "Path('SETUP_EXECUTED').write_text('unsafe')\n"
        "setup(name='dynamic', install_requires=deps)\n",
        encoding="utf-8",
    )

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root)

    assert captured.value.error_code == "DYNAMIC_SETUP_METADATA"
    assert captured.value.sources == ("setup.py",)
    assert not (root / "SETUP_EXECUTED").exists()


def test_explicit_dependency_paths_cannot_escape_project(tmp_path):
    root = materialize("no_tests", tmp_path / "project")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside==1\n", encoding="utf-8")

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root, DependencySelection(requirements_file="../outside.txt"))

    assert captured.value.error_code == "UNSAFE_DEPENDENCY_PATH"
    assert captured.value.sources == ("../outside.txt",)


def test_explicit_lock_and_requirements_are_mutually_exclusive(tmp_path):
    root = materialize("uv_locked", tmp_path / "project")
    (root / "requirements.txt").write_text("other==1\n", encoding="utf-8")

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(
            root,
            DependencySelection(lock_file="uv.lock", requirements_file="requirements.txt"),
        )

    assert captured.value.error_code == "AMBIGUOUS_DEPENDENCY_SOURCE"
    assert set(captured.value.sources) == {"uv.lock", "requirements.txt"}


def test_explicit_unknown_lock_type_is_rejected(tmp_path):
    root = materialize("no_runner", tmp_path / "project")
    (root / "custom.lock").write_text("version = 1\n", encoding="utf-8")

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root, DependencySelection(lock_file="custom.lock"))

    assert captured.value.error_code == "UNSUPPORTED_LOCK_FILE"
    assert captured.value.sources == ("custom.lock",)


@pytest.mark.parametrize(
    ("line", "error_code"),
    [
        ("--extra-index-url https://user:secret@example.invalid/simple", "UNSUPPORTED_REQUIREMENTS_DIRECTIVE"),
        ("-r nested.txt", "UNSUPPORTED_REQUIREMENTS_DIRECTIVE"),
        ("package @ https://example.invalid/package.whl", "UNSUPPORTED_DIRECT_REFERENCE"),
    ],
)
def test_requirements_cannot_smuggle_commands_or_direct_urls(tmp_path, line, error_code):
    root = tmp_path / "project"
    root.mkdir()
    (root / "requirements.txt").write_text(f"{line}\n", encoding="utf-8")

    with pytest.raises(DependencyPlanError) as captured:
        build_dependency_plan(root)

    assert captured.value.error_code == error_code
    assert captured.value.sources == ("requirements.txt",)


def test_plan_is_independent_from_unselected_requirement_files(tmp_path):
    root = materialize("uv_locked", tmp_path / "project")
    before = build_dependency_plan(root)
    (root / "requirements-dev.txt").write_text("unselected==1\n", encoding="utf-8")
    after = build_dependency_plan(root)

    assert after.fingerprint == before.fingerprint
    assert "unselected==1" not in after.declared_requirements


def test_copying_project_does_not_execute_setup_py(tmp_path):
    source = materialize("setup_py_only", tmp_path / "source")
    destination = tmp_path / "copy"

    shutil.copytree(source, destination)
    plan = build_dependency_plan(destination)

    assert plan.declared_requirements == ("fixture-dependency>=1",)
    assert not (destination / "SETUP_EXECUTED").exists()
