from __future__ import annotations

import configparser
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

PROFILE_PATH = Path(".promptopt/setup.json")


@dataclass(frozen=True, slots=True)
class ProjectSetupReport:
    project_root: str
    package_dir: str
    distribution_name: str
    import_name: str
    version: str
    required_imports: tuple[str, ...]
    metadata_directory: str
    import_validation: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def prepare_project(
    project_root: Path,
    package_dir: Path,
    environment: dict[str, str] | None = None,
    metadata_site: Path | None = None,
) -> tuple[ProjectSetupReport, dict[str, str]]:
    """Prepare a pure-Python source snapshot without executing repository setup scripts.

    The source directory is kept authoritative for coverage. A minimal ``dist-info``
    directory supplies package metadata required by projects such as isort, while a
    subprocess import preflight catches missing runtime dependencies before any LLM call.
    """

    root = project_root.resolve()
    package = package_dir.resolve()
    if root != package and root not in package.parents:
        raise RuntimeError("Package directory is outside the project workspace")
    if not package.is_dir():
        raise RuntimeError(f"Package directory does not exist: {package}")

    manifest_root = _manifest_root(root, package)
    profile = _load_profile(manifest_root)
    distribution_name = str(profile.get("distribution_name") or _distribution_name(manifest_root, package))
    detected_imports = _source_import_names(package)
    import_name = str(profile.get("import_name") or _primary_import_name(distribution_name, detected_imports))
    version = str(profile.get("version") or _project_version(manifest_root, package) or "0+local")
    # Do not eagerly import every top-level module. Some projects expose optional
    # modules whose dependencies are intentionally not part of the default install.
    required = tuple(dict.fromkeys([import_name, *profile.get("required_imports", [])]))

    metadata_site = (metadata_site or manifest_root / ".promptopt-site").resolve()
    metadata = metadata_site / f"{_canonical_name(distribution_name)}-{_safe_version(version)}.dist-info"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {distribution_name}\nVersion: {version}\n",
        encoding="utf-8",
    )

    prepared_environment = dict(environment or os.environ)
    import_root = package.parent if (package / "__init__.py").is_file() else package
    python_paths = [str(metadata_site), str(import_root), str(manifest_root)]
    if existing := prepared_environment.get("PYTHONPATH"):
        python_paths.append(existing)
    prepared_environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    validation = _validate_imports(
        distribution_name,
        required,
        prepared_environment,
        manifest_root,
    )
    return (
        ProjectSetupReport(
            project_root=str(manifest_root),
            package_dir=str(package),
            distribution_name=distribution_name,
            import_name=import_name,
            version=version,
            required_imports=required,
            metadata_directory=str(metadata),
            import_validation=validation,
        ),
        prepared_environment,
    )


def _manifest_root(project_root: Path, package_dir: Path) -> Path:
    manifests = ("pyproject.toml", "setup.cfg", "setup.py")
    current = package_dir.parent
    while current == project_root or project_root in current.parents:
        if any((current / name).is_file() for name in manifests):
            return current
        if current == project_root:
            break
        current = current.parent
    return project_root


def _load_profile(root: Path) -> dict:
    path = root / PROFILE_PATH
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("required_imports", []), list):
        raise RuntimeError("Invalid PromptOpt project setup profile")
    return value


def _distribution_name(root: Path, package_dir: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        value = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if name := value.get("project", {}).get("name"):
            return str(name)
    setup_cfg = root / "setup.cfg"
    if setup_cfg.is_file():
        parser = configparser.ConfigParser()
        parser.read(setup_cfg, encoding="utf-8")
        if parser.has_option("metadata", "name"):
            return parser.get("metadata", "name")
    setup_py = root / "setup.py"
    if setup_py.is_file():
        match = re.search(r"\bname\s*=\s*['\"]([^'\"]+)", setup_py.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return package_dir.name


def _project_version(root: Path, package_dir: Path) -> str | None:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        value = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if version := value.get("project", {}).get("version"):
            return str(version)
    setup_cfg = root / "setup.cfg"
    if setup_cfg.is_file():
        parser = configparser.ConfigParser()
        parser.read(setup_cfg, encoding="utf-8")
        if parser.has_option("metadata", "version"):
            version = parser.get("metadata", "version").strip()
            if version and not version.startswith("attr:"):
                return version
    for candidate in (package_dir / "__init__.py", package_dir / "_version.py"):
        if not candidate.is_file():
            continue
        match = re.search(
            r"\b__version__\s*=\s*['\"]([^'\"]+)['\"]",
            candidate.read_text(encoding="utf-8", errors="replace"),
        )
        if match:
            return match.group(1)
    return None


def _primary_import_name(distribution_name: str, imports: tuple[str, ...]) -> str:
    normalized = re.sub(r"[-.]+", "_", distribution_name)
    return normalized if normalized in imports else imports[0]


def _source_import_names(package_dir: Path) -> tuple[str, ...]:
    if (package_dir / "__init__.py").is_file():
        return (package_dir.name,)
    packages = sorted(item.name for item in package_dir.iterdir() if item.is_dir() and (item / "__init__.py").is_file())
    modules = sorted(
        item.stem for item in package_dir.glob("*.py") if item.name not in {"setup.py", "conftest.py", "__init__.py"}
    )
    imports = tuple(dict.fromkeys([*packages, *modules]))
    if not imports:
        raise RuntimeError(f"No importable Python package or module was found in {package_dir}")
    return imports


def _validate_imports(
    distribution_name: str,
    imports: tuple[str, ...],
    environment: dict[str, str],
    cwd: Path,
) -> str:
    command = [
        environment.get("TESTGEN_PYTHON", sys.executable),
        "-c",
        (
            "import importlib,importlib.metadata,sys; "
            "importlib.metadata.version(sys.argv[1]); "
            "[importlib.import_module(name) for name in sys.argv[2:]]"
        ),
        distribution_name,
        *imports,
    ]
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    if completed.returncode:
        detail = completed.stdout.strip()[-3000:]
        raise RuntimeError(f"Project environment preflight failed: {detail}")
    return "passed"


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "_", value).strip("_") or "project"


def _safe_version(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+!-]+", ".", value).strip(".") or "0+promptopt"
