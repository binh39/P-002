from __future__ import annotations

from packaging.version import Version


def classify_version(raw: str) -> str:
    """Classify a version through stable, preview, and legacy paths."""
    version = Version(raw)
    if version.major >= 2:
        return "modern"
    if version.is_prerelease:
        return "preview"
    return "legacy"
