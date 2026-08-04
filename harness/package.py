from __future__ import annotations

import re
import tomllib
from pathlib import Path


def _project_name(package_dir: Path) -> str:
    pyproject = package_dir.parent / "pyproject.toml"
    if pyproject.exists():
        try:
            project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get(
                "project", {}
            )
            if project.get("name"):
                return str(project["name"])
        except (OSError, tomllib.TOMLDecodeError):
            pass
    return package_dir.name


def add_distribution_metadata(package_dir: Path, destination_root: Path) -> Path:
    """Make a copied source package visible to importlib.metadata in a sandbox."""
    name = _project_name(package_dir)
    normalized = re.sub(r"[-_.]+", "_", name)
    metadata_dir = destination_root / f"{normalized}-0.0.0.dist-info"
    metadata_dir.mkdir(exist_ok=True)
    (metadata_dir / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 0.0.0\n",
        encoding="utf-8",
    )
    return metadata_dir
