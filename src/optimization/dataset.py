from __future__ import annotations

import json
from collections import Counter
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


def validate_project_stratification(
    targets_by_split: dict[str, list[SymbolTarget]],
) -> None:
    """Require every split to have the same near-proportional project mix."""

    nonempty = {
        split: targets for split, targets in targets_by_split.items() if targets
    }
    if len(nonempty) < 2:
        return
    all_targets = [target for targets in nonempty.values() for target in targets]
    overall = Counter(target.project for target in all_targets)
    projects = set(overall)
    total = len(all_targets)
    problems = []
    for split, targets in nonempty.items():
        counts = Counter(target.project for target in targets)
        if set(counts) != projects:
            missing = sorted(projects - set(counts))
            extra = sorted(set(counts) - projects)
            problems.append(f"{split}: missing={missing}, extra={extra}")
            continue
        for project in sorted(projects):
            expected = len(targets) * overall[project] / total
            if abs(counts[project] - expected) > 1.0:
                problems.append(
                    f"{split}/{project}: got {counts[project]}, "
                    f"expected about {expected:.1f}"
                )
    if problems:
        details = "; ".join(problems[:12])
        raise ValueError(
            "Dataset splits are not stratified by project. Rebuild them with "
            f"scripts/build_ranked_dataset.py. Details: {details}"
        )
