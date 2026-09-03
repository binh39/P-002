"""Canonical, non-executable dependency planning for project sandboxes."""

from __future__ import annotations

import ast
import configparser
import hashlib
import json
import re

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by Python 3.10 image contract
    import tomli as tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement

from cloud.sandbox_contract import DependencyMode
from cloud.sandbox_metadata import ProjectMetadataError, PythonResolution, resolve_python_metadata

DEPENDENCY_PLAN_VERSION = 1
_INDEX_REFERENCE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")


class DependencyPlanError(ValueError):
    def __init__(self, error_code: str, message: str, sources: tuple[str, ...]):
        self.error_code = error_code
        self.sources = sources
        rendered = ", ".join(sources) if sources else "<project>"
        super().__init__(f"{message} [sources: {rendered}]")

    def as_dict(self) -> dict[str, Any]:
        return {"error_code": self.error_code, "message": str(self), "sources": list(self.sources)}


class DependencySource(str, Enum):  # noqa: UP042 - sandbox metadata supports Python 3.10
    UV_LOCK = "uv_lock"
    POETRY_LOCK = "poetry_lock"
    REQUIREMENTS = "requirements"
    PYPROJECT = "pyproject"
    SETUP_CFG = "setup_cfg"
    SETUP_PY = "setup_py"
    NONE = "none"


class InstallTarget(str, Enum):  # noqa: UP042 - sandbox metadata supports Python 3.10
    DEPENDENCIES_ONLY = "dependencies_only"
    PROJECT = "project"


@dataclass(frozen=True, slots=True)
class DependencySelection:
    lock_file: str | None = None
    requirements_file: str | None = None
    groups: tuple[str, ...] = ()
    extras: tuple[str, ...] = ()
    package_index_refs: tuple[str, ...] = ()
    install_target: InstallTarget = InstallTarget.DEPENDENCIES_ONLY


@dataclass(frozen=True, slots=True)
class DependencyPlan:
    source: DependencySource
    mode: DependencyMode
    manifest: str | None
    lock_file: str | None
    groups: tuple[str, ...]
    extras: tuple[str, ...]
    package_index_refs: tuple[str, ...]
    install_target: InstallTarget
    declared_requirements: tuple[str, ...]
    python: PythonResolution
    input_digests: tuple[tuple[str, str], ...]
    fingerprint: str
    plan_version: int = DEPENDENCY_PLAN_VERSION

    def canonical_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {
            "plan_version": self.plan_version,
            "source": self.source.value,
            "mode": self.mode.value,
            "manifest": self.manifest,
            "lock_file": self.lock_file,
            "groups": list(self.groups),
            "extras": list(self.extras),
            "package_index_refs": list(self.package_index_refs),
            "install_target": self.install_target.value,
            "declared_requirements": list(self.declared_requirements),
            "python": self.python.as_dict(),
            "input_digests": [{"path": path, "sha256": digest} for path, digest in self.input_digests],
        }
        if include_fingerprint:
            payload["fingerprint"] = self.fingerprint
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DependencyPlan:
        plan = cls(
            source=DependencySource(payload["source"]),
            mode=DependencyMode(payload["mode"]),
            manifest=payload.get("manifest"),
            lock_file=payload.get("lock_file"),
            groups=tuple(payload.get("groups", ())),
            extras=tuple(payload.get("extras", ())),
            package_index_refs=tuple(payload.get("package_index_refs", ())),
            install_target=InstallTarget(payload["install_target"]),
            declared_requirements=tuple(payload.get("declared_requirements", ())),
            python=PythonResolution.from_dict(payload["python"]),
            input_digests=tuple((item["path"], item["sha256"]) for item in payload.get("input_digests", ())),
            fingerprint=str(payload["fingerprint"]),
            plan_version=int(payload.get("plan_version", DEPENDENCY_PLAN_VERSION)),
        )
        if plan.plan_version != DEPENDENCY_PLAN_VERSION:
            raise ValueError("Unsupported dependency plan version")
        expected = hashlib.sha256(
            json.dumps(
                plan.canonical_dict(include_fingerprint=False),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if expected != plan.fingerprint:
            raise ValueError("Dependency plan fingerprint mismatch")
        return plan


def _safe_relative_file(root: Path, value: str, *, field: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value.strip():
        raise DependencyPlanError("INVALID_DEPENDENCY_PATH", f"{field} must be a non-empty path", (field,))
    normalized = value.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or ".." in relative.parts or normalized.startswith("//"):
        raise DependencyPlanError(
            "UNSAFE_DEPENDENCY_PATH",
            f"{field} must stay inside the project root",
            (value,),
        )
    root = root.resolve()
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DependencyPlanError(
            "UNSAFE_DEPENDENCY_PATH",
            f"{field} resolves outside the project root",
            (value,),
        ) from exc
    if not candidate.is_file():
        raise DependencyPlanError("DEPENDENCY_FILE_NOT_FOUND", f"{field} does not exist", (relative.as_posix(),))
    return relative.as_posix(), candidate


def _read_toml(path: Path, relative: str) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise DependencyPlanError(
            "INVALID_DEPENDENCY_METADATA", f"Could not parse {relative}: {exc}", (relative,)
        ) from exc


def _select_source(root: Path, selection: DependencySelection) -> tuple[DependencySource, str | None, str | None]:
    if selection.lock_file and selection.requirements_file:
        raise DependencyPlanError(
            "AMBIGUOUS_DEPENDENCY_SOURCE",
            "Choose a lock file or a requirements file, not both",
            (selection.lock_file, selection.requirements_file),
        )
    if selection.lock_file:
        lock_relative, _ = _safe_relative_file(root, selection.lock_file, field="lock_file")
        lock_name = Path(lock_relative).name
        if lock_name not in {"uv.lock", "poetry.lock"}:
            raise DependencyPlanError(
                "UNSUPPORTED_LOCK_FILE",
                "Only uv.lock and poetry.lock are supported",
                (lock_relative,),
            )
        if not (root / "pyproject.toml").is_file():
            raise DependencyPlanError(
                "LOCK_WITHOUT_MANIFEST",
                f"{lock_name} requires pyproject.toml",
                (lock_relative,),
            )
        source = DependencySource.POETRY_LOCK if lock_name == "poetry.lock" else DependencySource.UV_LOCK
        return source, "pyproject.toml", lock_relative
    if (root / "uv.lock").is_file():
        if not (root / "pyproject.toml").is_file():
            raise DependencyPlanError("LOCK_WITHOUT_MANIFEST", "uv.lock requires pyproject.toml", ("uv.lock",))
        return DependencySource.UV_LOCK, "pyproject.toml", "uv.lock"
    if (root / "poetry.lock").is_file():
        if not (root / "pyproject.toml").is_file():
            raise DependencyPlanError("LOCK_WITHOUT_MANIFEST", "poetry.lock requires pyproject.toml", ("poetry.lock",))
        return DependencySource.POETRY_LOCK, "pyproject.toml", "poetry.lock"
    if selection.requirements_file:
        relative, _ = _safe_relative_file(root, selection.requirements_file, field="requirements_file")
        return DependencySource.REQUIREMENTS, relative, None
    for filename, source in (
        ("requirements.txt", DependencySource.REQUIREMENTS),
        ("pyproject.toml", DependencySource.PYPROJECT),
        ("setup.cfg", DependencySource.SETUP_CFG),
        ("setup.py", DependencySource.SETUP_PY),
    ):
        if (root / filename).is_file():
            return source, filename, None
    return DependencySource.NONE, None, None


def _validate_index_refs(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(set(values)) != len(values):
        raise DependencyPlanError("DUPLICATE_PACKAGE_INDEX", "Package index references cannot repeat", values)
    for value in values:
        if not _INDEX_REFERENCE.fullmatch(value):
            raise DependencyPlanError(
                "INVALID_PACKAGE_INDEX_REFERENCE",
                "Package indexes must be credential-free reference names, not URLs or secret values",
                (value,),
            )
    return values


def _string_requirements(value: Any, *, source: str, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise DependencyPlanError(
            "INVALID_DEPENDENCY_METADATA",
            f"{field} must be an array of requirement strings",
            (source,),
        )
    return tuple(item.strip() for item in value)


def _poetry_requirement(name: str, value: Any, *, source: str) -> str:
    def render_version(version: str) -> str:
        if version == "*":
            return name
        if version.startswith("^"):
            raw = version[1:]
            parts = raw.split(".")
            if not parts or not all(part.isdigit() for part in parts):
                raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Invalid Poetry dependency {name}", (source,))
            major = int(parts[0])
            if major:
                upper = f"{major + 1}.0"
            elif len(parts) > 1 and int(parts[1]):
                upper = f"0.{int(parts[1]) + 1}"
            else:
                patch = int(parts[2]) if len(parts) > 2 else 0
                upper = f"0.0.{patch + 1}"
            return f"{name}>={raw},<{upper}"
        if version.startswith("~") and not version.startswith("~="):
            raw = version[1:]
            parts = raw.split(".")
            if len(parts) < 2 or not all(part.isdigit() for part in parts):
                raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Invalid Poetry dependency {name}", (source,))
            return f"{name}>={raw},<{parts[0]}.{int(parts[1]) + 1}"
        return f"{name}{version}"

    if isinstance(value, str):
        return render_version(value)
    if isinstance(value, dict):
        version = value.get("version", "*")
        if not isinstance(version, str):
            raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Invalid Poetry dependency {name}", (source,))
        marker = value.get("markers")
        rendered = render_version(version)
        if marker is not None:
            if not isinstance(marker, str):
                raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Invalid Poetry marker for {name}", (source,))
            rendered = f"{rendered}; {marker}"
        return rendered
    raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Invalid Poetry dependency {name}", (source,))


def _pyproject_inputs(
    payload: dict[str, Any],
    *,
    source: str,
    selected_groups: tuple[str, ...],
    selected_extras: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    requirements: list[str] = []
    project = payload.get("project", {})
    if isinstance(project, dict):
        requirements.extend(
            _string_requirements(project.get("dependencies", []), source=source, field="project.dependencies")
        )
    poetry = payload.get("tool", {}).get("poetry", {})
    if isinstance(poetry, dict):
        poetry_dependencies = poetry.get("dependencies", {})
        if isinstance(poetry_dependencies, dict):
            requirements.extend(
                _poetry_requirement(name, value, source=source)
                for name, value in sorted(poetry_dependencies.items())
                if name.casefold() != "python"
            )

    dependency_groups = payload.get("dependency-groups", {})
    if dependency_groups is None:
        dependency_groups = {}
    if not isinstance(dependency_groups, dict):
        raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", "dependency-groups must be a table", (source,))
    poetry_groups = poetry.get("group", {}) if isinstance(poetry, dict) else {}
    if poetry_groups is None:
        poetry_groups = {}
    if not isinstance(poetry_groups, dict):
        raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", "tool.poetry.group must be a table", (source,))
    available_groups = tuple(sorted(set(dependency_groups) | set(poetry_groups)))

    optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
    if optional is None:
        optional = {}
    if not isinstance(optional, dict):
        raise DependencyPlanError(
            "INVALID_DEPENDENCY_METADATA", "project.optional-dependencies must be a table", (source,)
        )
    poetry_extras = poetry.get("extras", {}) if isinstance(poetry, dict) else {}
    if poetry_extras is None:
        poetry_extras = {}
    if not isinstance(poetry_extras, dict):
        raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", "tool.poetry.extras must be a table", (source,))
    available_extras = tuple(sorted(set(optional) | set(poetry_extras)))

    missing_groups = set(selected_groups) - set(available_groups)
    missing_extras = set(selected_extras) - set(available_extras)
    if missing_groups:
        raise DependencyPlanError(
            "UNKNOWN_DEPENDENCY_GROUP",
            f"Unknown dependency groups: {', '.join(sorted(missing_groups))}",
            (source,),
        )
    if missing_extras:
        raise DependencyPlanError(
            "UNKNOWN_DEPENDENCY_EXTRA",
            f"Unknown dependency extras: {', '.join(sorted(missing_extras))}",
            (source,),
        )

    for group in selected_groups:
        if group in dependency_groups:
            requirements.extend(
                _string_requirements(dependency_groups[group], source=source, field=f"dependency-groups.{group}")
            )
        else:
            group_payload = poetry_groups[group]
            if not isinstance(group_payload, dict) or not isinstance(group_payload.get("dependencies", {}), dict):
                raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Invalid Poetry group {group}", (source,))
            requirements.extend(
                _poetry_requirement(name, value, source=source)
                for name, value in sorted(group_payload.get("dependencies", {}).items())
            )
    for extra in selected_extras:
        if extra in optional:
            requirements.extend(
                _string_requirements(optional[extra], source=source, field=f"project.optional-dependencies.{extra}")
            )
        else:
            references = poetry_extras[extra]
            requirements.extend(_string_requirements(references, source=source, field=f"tool.poetry.extras.{extra}"))
    return tuple(requirements), available_groups, available_extras


def _requirements_file(path: Path, source: str) -> tuple[str, ...]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise DependencyPlanError("INVALID_DEPENDENCY_METADATA", f"Could not read {source}: {exc}", (source,)) from exc
    requirements = tuple(line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#"))
    for item in requirements:
        if item.startswith("-"):
            raise DependencyPlanError(
                "UNSUPPORTED_REQUIREMENTS_DIRECTIVE",
                "Requirements files cannot include commands, nested files, constraints, or index options",
                (source,),
            )
        try:
            parsed = Requirement(item)
        except InvalidRequirement as exc:
            raise DependencyPlanError(
                "INVALID_DEPENDENCY_METADATA", f"Invalid requirement {item!r}", (source,)
            ) from exc
        if parsed.url:
            raise DependencyPlanError(
                "UNSUPPORTED_DIRECT_REFERENCE",
                "Direct URL/path requirements are not allowed; use an allowlisted package index reference",
                (source,),
            )
    return requirements


def _setup_cfg_requirements(path: Path) -> tuple[str, ...]:
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except (OSError, UnicodeError, configparser.Error) as exc:
        raise DependencyPlanError(
            "INVALID_DEPENDENCY_METADATA", f"Could not parse setup.cfg: {exc}", ("setup.cfg",)
        ) from exc
    if not parser.has_option("options", "install_requires"):
        return ()
    return tuple(line.strip() for line in parser.get("options", "install_requires").splitlines() if line.strip())


def _setup_py_requirements(path: Path) -> tuple[str, ...]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise DependencyPlanError(
            "INVALID_DEPENDENCY_METADATA", f"Could not parse setup.py: {exc}", ("setup.py",)
        ) from exc
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
        if function_name != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg == "install_requires":
                try:
                    value = ast.literal_eval(keyword.value)
                except (ValueError, TypeError, SyntaxError) as exc:
                    raise DependencyPlanError(
                        "DYNAMIC_SETUP_METADATA",
                        "setup.py install_requires must be a static string list",
                        ("setup.py",),
                    ) from exc
                return _string_requirements(value, source="setup.py", field="setup(install_requires=...)")
    return ()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unique(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if len(set(values)) != len(values):
        raise DependencyPlanError(f"DUPLICATE_{field.upper()}", f"{field} cannot contain duplicates", values)
    return values


def build_dependency_plan(root: Path, selection: DependencySelection | None = None) -> DependencyPlan:
    root = root.resolve()
    if not root.is_dir():
        raise DependencyPlanError("PROJECT_ROOT_NOT_FOUND", "Project root does not exist", (str(root),))
    selection = selection or DependencySelection()
    groups = tuple(sorted(_unique(tuple(selection.groups), field="groups")))
    extras = tuple(sorted(_unique(tuple(selection.extras), field="extras")))
    index_refs = _validate_index_refs(tuple(selection.package_index_refs))
    try:
        python = resolve_python_metadata(root)
    except ProjectMetadataError as exc:
        raise DependencyPlanError(exc.error_code, str(exc), exc.sources) from exc

    source, manifest, lock_file = _select_source(root, selection)
    mode = (
        DependencyMode.NONE
        if source == DependencySource.NONE
        else DependencyMode.LOCKED
        if lock_file
        else DependencyMode.MANIFEST
    )
    requirements: tuple[str, ...] = ()
    input_paths: list[tuple[str, Path]] = []

    pyproject_payload: dict[str, Any] | None = None
    available_groups: tuple[str, ...] = ()
    available_extras: tuple[str, ...] = ()
    if manifest:
        manifest_relative, manifest_path = _safe_relative_file(root, manifest, field="manifest")
        input_paths.append((manifest_relative, manifest_path))
        if manifest_relative == "pyproject.toml":
            pyproject_payload = _read_toml(manifest_path, manifest_relative)
            _, available_groups, available_extras = _pyproject_inputs(
                pyproject_payload,
                source=manifest_relative,
                selected_groups=(),
                selected_extras=(),
            )
            if not groups and "test" in available_groups:
                groups = ("test",)
            requirements, _, _ = _pyproject_inputs(
                pyproject_payload,
                source=manifest_relative,
                selected_groups=groups,
                selected_extras=extras,
            )
        elif source == DependencySource.REQUIREMENTS:
            if groups or extras:
                raise DependencyPlanError(
                    "UNSUPPORTED_DEPENDENCY_SELECTION",
                    "Requirements-file mode does not support groups or extras",
                    (manifest_relative,),
                )
            requirements = _requirements_file(manifest_path, manifest_relative)
        elif source == DependencySource.SETUP_CFG:
            if groups or extras:
                raise DependencyPlanError(
                    "UNSUPPORTED_DEPENDENCY_SELECTION",
                    "setup.cfg mode does not support groups or extras",
                    (manifest_relative,),
                )
            requirements = _setup_cfg_requirements(manifest_path)
        elif source == DependencySource.SETUP_PY:
            if groups or extras:
                raise DependencyPlanError(
                    "UNSUPPORTED_DEPENDENCY_SELECTION",
                    "setup.py mode does not support groups or extras",
                    (manifest_relative,),
                )
            requirements = _setup_py_requirements(manifest_path)

    if lock_file:
        lock_relative, lock_path = _safe_relative_file(root, lock_file, field="lock_file")
        input_paths.append((lock_relative, lock_path))
        _read_toml(lock_path, lock_relative)

    if source == DependencySource.NONE and (groups or extras):
        raise DependencyPlanError(
            "UNSUPPORTED_DEPENDENCY_SELECTION",
            "A project without dependency metadata cannot select groups or extras",
            tuple((*groups, *extras)),
        )

    input_digests = tuple((relative, _digest(path)) for relative, path in sorted(input_paths))
    base = {
        "plan_version": DEPENDENCY_PLAN_VERSION,
        "source": source.value,
        "mode": mode.value,
        "manifest": manifest,
        "lock_file": lock_file,
        "groups": list(groups),
        "extras": list(extras),
        "package_index_refs": list(index_refs),
        "install_target": selection.install_target.value,
        "declared_requirements": list(requirements),
        "python": python.as_dict(),
        "input_digests": [{"path": path, "sha256": digest} for path, digest in input_digests],
    }
    fingerprint = hashlib.sha256(
        json.dumps(base, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return DependencyPlan(
        source=source,
        mode=mode,
        manifest=manifest,
        lock_file=lock_file,
        groups=groups,
        extras=extras,
        package_index_refs=index_refs,
        install_target=selection.install_target,
        declared_requirements=requirements,
        python=python,
        input_digests=input_digests,
        fingerprint=fingerprint,
    )
