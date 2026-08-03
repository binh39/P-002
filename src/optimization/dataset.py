from __future__ import annotations

import json
from pathlib import Path

from .models import SymbolTarget


def load_targets(path: Path, split: str | None = None) -> list[SymbolTarget]:
    targets = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                target = SymbolTarget.from_dict(json.loads(line))
            except (TypeError, KeyError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid target at {path}:{line_number}: {exc}") from exc
            if split is None or target.split == split:
                targets.append(target)
    return targets
