from __future__ import annotations

import os
import tempfile
from pathlib import Path


def temporary_workspace(prefix: str) -> tempfile.TemporaryDirectory[str]:
    shared_root = os.getenv("TESTGEN_SHARED_WORKSPACE", "").strip()
    if shared_root:
        root = Path(shared_root)
        root.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(
            prefix=prefix,
            dir=root,
            ignore_cleanup_errors=True,
        )
    return tempfile.TemporaryDirectory(
        prefix=prefix,
        ignore_cleanup_errors=True,
    )


def docker_mount(
    path: Path,
    destination: str,
    *,
    read_only: bool,
) -> list[str]:
    """Build a bind mount locally or a volume-subpath mount inside Compose."""
    shared_root = os.getenv("TESTGEN_SHARED_WORKSPACE", "").strip()
    volume = os.getenv("TESTGEN_DOCKER_WORKSPACE_VOLUME", "").strip()
    if bool(shared_root) != bool(volume):
        raise RuntimeError(
            "TESTGEN_SHARED_WORKSPACE and "
            "TESTGEN_DOCKER_WORKSPACE_VOLUME must be configured together"
        )
    if not volume:
        mode = "ro" if read_only else "rw"
        return ["-v", f"{path}:{destination}:{mode}"]

    root = Path(shared_root).resolve()
    selected = path.resolve()
    try:
        relative = selected.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Shared mount path {selected} is outside {root}") from exc
    specification = (
        f"type=volume,src={volume},dst={destination},volume-subpath={relative}"
    )
    if read_only:
        specification += ",readonly"
    return ["--mount", specification]
