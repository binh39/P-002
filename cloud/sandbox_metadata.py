"""Static Python metadata discovery for uploaded projects.

All project files are parsed as data.  In particular, ``setup.py`` is parsed
with ``ast`` and is never imported or executed.
"""

from __future__ import annotations

import ast
import configparser
import re

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by Python 3.10 image contract
    import tomli as tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

DEFAULT_PYTHON_VERSION = "3.12"
SUPPORTED_PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13")
_PYTHON_HINT = re.compile(r"^(?:python-)?(3\.(?:10|11|12|13))(?:\.\d+)?$")


class ProjectMetadataError(ValueError):
    """A bounded metadata diagnostic that always identifies its sources."""

    def __init__(self, error_code: str, message: str, sources: tuple[str, ...]):
        self.error_code = error_code
        self.sources = sources
        rendered = ", ".join(sources) if sources else "<project>"
        super().__init__(f"{message} [sources: {rendered}]")

    def as_dict(self) -> dict[str, Any]:
        return {"error_code": self.error_code, "message": str(self), "sources": list(self.sources)}


@dataclass(frozen=True, slots=True)
class PythonRequirementSource:
    path: str
    field: str
    raw_value: str
    specifier: str
    priority: int
    hint: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "field": self.field,
            "raw_value": self.raw_value,
            "specifier": self.specifier,
            "priority": self.priority,
            "hint": self.hint,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PythonRequirementSource:
        return cls(
            path=str(payload["path"]),
            field=str(payload["field"]),
            raw_value=str(payload["raw_value"]),
            specifier=str(payload["specifier"]),
            priority=int(payload["priority"]),
            hint=bool(payload.get("hint", False)),
        )


@dataclass(frozen=True, slots=True)
class PythonResolution:
    python_version: str
    combined_specifier: str
    inferred: bool
    sources: tuple[PythonRequirementSource, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "combined_specifier": self.combined_specifier,
            "inferred": self.inferred,
            "sources": [source.as_dict() for source in self.sources],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PythonResolution:
        return cls(
            python_version=str(payload["python_version"]),
            combined_specifier=str(payload["combined_specifier"]),
            inferred=bool(payload["inferred"]),
            sources=tuple(PythonRequirementSource.from_dict(item) for item in payload["sources"]),
        )


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ProjectMetadataError("INVALID_TOML", f"Could not parse {path.name}: {exc}", (path.name,)) from exc


def _string_value(value: Any, *, path: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectMetadataError(
            "INVALID_PYTHON_REQUIREMENT",
            f"{field} must be a non-empty string",
            (path,),
        )
    return value.strip()


def _poetry_to_pep440(value: str, *, path: str, field: str) -> str:
    value = value.strip()
    if value.startswith("^"):
        version = value[1:]
        parts = version.split(".")
        if not all(part.isdigit() for part in parts):
            raise ProjectMetadataError("INVALID_PYTHON_REQUIREMENT", f"Invalid Poetry constraint {value!r}", (path,))
        major = int(parts[0])
        if major > 0:
            upper = f"{major + 1}.0"
        elif len(parts) > 1 and int(parts[1]) > 0:
            upper = f"0.{int(parts[1]) + 1}"
        else:
            patch = int(parts[2]) if len(parts) > 2 else 0
            upper = f"0.0.{patch + 1}"
        return f">={version},<{upper}"
    if value.startswith("~") and not value.startswith("~="):
        version = value[1:]
        parts = version.split(".")
        if len(parts) < 2 or not all(part.isdigit() for part in parts):
            raise ProjectMetadataError("INVALID_PYTHON_REQUIREMENT", f"Invalid Poetry constraint {value!r}", (path,))
        return f">={version},<{parts[0]}.{int(parts[1]) + 1}"
    if value == "*":
        return ">=0"
    return value


def _validate_specifier(value: str, *, path: str, field: str) -> str:
    try:
        SpecifierSet(value)
    except InvalidSpecifier as exc:
        raise ProjectMetadataError(
            "INVALID_PYTHON_REQUIREMENT",
            f"Invalid Python requirement {value!r} in {field}",
            (path,),
        ) from exc
    return value


def _source(
    *,
    path: str,
    field: str,
    value: Any,
    priority: int,
    poetry: bool = False,
    hint: bool = False,
) -> PythonRequirementSource:
    raw = _string_value(value, path=path, field=field)
    specifier = _poetry_to_pep440(raw, path=path, field=field) if poetry else raw
    return PythonRequirementSource(
        path=path,
        field=field,
        raw_value=raw,
        specifier=_validate_specifier(specifier, path=path, field=field),
        priority=priority,
        hint=hint,
    )


def _setup_py_python_requires(path: Path) -> str | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ProjectMetadataError(
            "INVALID_SETUP_PY", f"Could not statically parse setup.py: {exc}", (path.name,)
        ) from exc
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
        if function_name != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg == "python_requires":
                try:
                    value = ast.literal_eval(keyword.value)
                except (ValueError, TypeError, SyntaxError) as exc:
                    raise ProjectMetadataError(
                        "DYNAMIC_SETUP_METADATA",
                        "setup.py python_requires must be a static string literal",
                        (path.name,),
                    ) from exc
                if not isinstance(value, str):
                    raise ProjectMetadataError(
                        "DYNAMIC_SETUP_METADATA",
                        "setup.py python_requires must be a static string literal",
                        (path.name,),
                    )
                return value
    return None


def _hint_source(path: Path, *, field: str, priority: int) -> PythonRequirementSource | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except (OSError, UnicodeError, IndexError) as exc:
        raise ProjectMetadataError("INVALID_PYTHON_HINT", f"Could not read {path.name}", (path.name,)) from exc
    match = _PYTHON_HINT.fullmatch(raw)
    if not match:
        raise ProjectMetadataError(
            "INVALID_PYTHON_HINT",
            f"{path.name} must contain python-3.10..3.13 or 3.10..3.13",
            (path.name,),
        )
    minor = match.group(1)
    return _source(path=path.name, field=field, value=f"=={minor}.*", priority=priority, hint=True)


def discover_python_requirement_sources(root: Path) -> tuple[PythonRequirementSource, ...]:
    """Collect Python constraints in deterministic priority order."""

    root = root.resolve()
    sources: list[PythonRequirementSource] = []
    pyproject_path = root / "pyproject.toml"
    pyproject: dict[str, Any] = {}
    if pyproject_path.is_file():
        pyproject = _read_toml(pyproject_path)
        project = pyproject.get("project")
        if isinstance(project, dict) and "requires-python" in project:
            sources.append(
                _source(
                    path="pyproject.toml",
                    field="[project].requires-python",
                    value=project["requires-python"],
                    priority=10,
                )
            )
        poetry_dependencies = pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {})
        if isinstance(poetry_dependencies, dict) and "python" in poetry_dependencies:
            sources.append(
                _source(
                    path="pyproject.toml",
                    field="[tool.poetry.dependencies].python",
                    value=poetry_dependencies["python"],
                    priority=20,
                    poetry=True,
                )
            )

    uv_lock_path = root / "uv.lock"
    if uv_lock_path.is_file():
        uv_lock = _read_toml(uv_lock_path)
        if "requires-python" in uv_lock:
            sources.append(
                _source(
                    path="uv.lock",
                    field="requires-python",
                    value=uv_lock["requires-python"],
                    priority=30,
                )
            )

    poetry_lock_path = root / "poetry.lock"
    if poetry_lock_path.is_file():
        poetry_lock = _read_toml(poetry_lock_path)
        poetry_python = poetry_lock.get("python-versions")
        if poetry_python is None and isinstance(poetry_lock.get("metadata"), dict):
            poetry_python = poetry_lock["metadata"].get("python-versions")
        if poetry_python is not None:
            sources.append(
                _source(
                    path="poetry.lock",
                    field="python-versions",
                    value=poetry_python,
                    priority=40,
                    poetry=True,
                )
            )

    setup_cfg_path = root / "setup.cfg"
    if setup_cfg_path.is_file():
        parser = configparser.ConfigParser()
        try:
            parser.read(setup_cfg_path, encoding="utf-8")
        except (OSError, UnicodeError, configparser.Error) as exc:
            raise ProjectMetadataError(
                "INVALID_SETUP_CFG", f"Could not parse setup.cfg: {exc}", ("setup.cfg",)
            ) from exc
        if parser.has_option("options", "python_requires"):
            sources.append(
                _source(
                    path="setup.cfg",
                    field="[options].python_requires",
                    value=parser.get("options", "python_requires"),
                    priority=50,
                )
            )

    setup_py_path = root / "setup.py"
    if setup_py_path.is_file():
        setup_requirement = _setup_py_python_requires(setup_py_path)
        if setup_requirement is not None:
            sources.append(
                _source(
                    path="setup.py",
                    field="setup(python_requires=...)",
                    value=setup_requirement,
                    priority=60,
                )
            )

    for hint in (
        _hint_source(root / ".python-version", field="python version hint", priority=70),
        _hint_source(root / "runtime.txt", field="runtime version hint", priority=80),
    ):
        if hint is not None:
            sources.append(hint)
    return tuple(sorted(sources, key=lambda item: (item.priority, item.path, item.field)))


def _minor_is_allowed(minor: str, sources: tuple[PythonRequirementSource, ...]) -> bool:
    # Runtime routing is minor-based, while uploaded metadata may contain an
    # exact patch pin. Cover the complete practical CPython patch range rather
    # than sampling a few values and incorrectly rejecting e.g. ``3.12.50``.
    candidates = [Version(f"{minor}.{patch}") for patch in range(1000)]
    return any(all(candidate in SpecifierSet(source.specifier) for source in sources) for candidate in candidates)


def resolve_python_metadata(root: Path, *, default: str = DEFAULT_PYTHON_VERSION) -> PythonResolution:
    sources = discover_python_requirement_sources(root)
    if not sources:
        if default not in SUPPORTED_PYTHON_VERSIONS:
            raise ProjectMetadataError(
                "UNSUPPORTED_DEFAULT_PYTHON", f"Unsupported default Python {default}", ("policy",)
            )
        return PythonResolution(default, f"=={default}.*", True, ())

    compatible = tuple(version for version in SUPPORTED_PYTHON_VERSIONS if _minor_is_allowed(version, sources))
    if not compatible:
        details = "; ".join(f"{item.path}:{item.field}={item.raw_value!r}" for item in sources)
        raise ProjectMetadataError(
            "CONFLICTING_PYTHON_METADATA",
            f"Python metadata has no supported common version: {details}",
            tuple(dict.fromkeys(item.path for item in sources)),
        )

    selected = default if default in compatible else compatible[-1]
    combined = ",".join(source.specifier for source in sources)
    return PythonResolution(selected, combined, False, sources)
