import hashlib
import random
from collections.abc import Iterable

from .schemas import DatasetPercentages, SamplingMethod, TargetReference


def _stable_key(target: TargetReference) -> str:
    return f"{target.project_id}::{target.function_id}"


def select_targets(
    targets: Iterable[TargetReference],
    method: SamplingMethod,
    seed: int,
    max_targets: int | None = None,
) -> list[TargetReference]:
    """Build a deterministic candidate pool using the Cloud pipeline selection rules."""
    candidates = sorted(targets, key=_stable_key)
    if max_targets is not None:
        max_targets = min(max_targets, len(candidates))
    else:
        max_targets = len(candidates)
    rng = random.Random(seed)
    if method == SamplingMethod.RANDOM:
        rng.shuffle(candidates)
        return candidates[:max_targets]
    if method == SamplingMethod.MOST_BRANCHES:
        candidates.sort(key=lambda item: (-item.branches, -item.statements, -item.loc, _stable_key(item)))
    elif method == SamplingMethod.MOST_STATEMENTS:
        candidates.sort(key=lambda item: (-item.statements, -item.branches, -item.loc, _stable_key(item)))
    else:
        raise ValueError("Manual targets must be supplied as explicit dataset splits")
    selected = candidates[:max_targets]
    rng.shuffle(selected)
    return selected


def split_targets(
    targets: Iterable[TargetReference],
    percentages: DatasetPercentages | None = None,
    seed: int = 7,
) -> dict[str, list[str]]:
    """Create stable, disjoint, project-stratified dataset splits."""
    percentages = percentages or DatasetPercentages()
    unique = {_stable_key(target): target for target in targets}
    counts = _allocate_counts(len(unique), percentages)
    split_names = tuple(counts)
    projects: dict[str, list[str]] = {}
    for key, target in unique.items():
        projects.setdefault(target.project_id, []).append(key)
    if not projects:
        return {name: [] for name in split_names}

    positive_splits = tuple(name for name in split_names if counts[name] > 0)
    project_count = len(projects)
    if any(counts[name] < project_count for name in positive_splits):
        raise ValueError("Dataset is too small to include every project in every non-empty split")
    undersized = sorted(project for project, values in projects.items() if len(values) < len(positive_splits))
    if undersized:
        raise ValueError(
            "Each project needs at least one target in every non-empty split; "
            f"undersized projects: {', '.join(undersized[:10])}"
        )

    # Reserve one target per project in every active split, then distribute the
    # remainder toward the proportional ideal while preserving exact totals.
    total = len(unique)
    allocation = {(project, split): int(split in positive_splits) for project in projects for split in split_names}
    row_remaining = {project: len(values) - len(positive_splits) for project, values in projects.items()}
    column_remaining = {
        split: counts[split] - project_count if split in positive_splits else 0 for split in split_names
    }
    while any(column_remaining.values()):
        candidates = [
            (
                len(projects[project]) * counts[split] / total - allocation[(project, split)],
                project,
                split,
            )
            for project in sorted(projects)
            for split in split_names
            if row_remaining[project] > 0 and column_remaining[split] > 0
        ]
        if not candidates:
            raise ValueError("Unable to satisfy project-stratified split sizes")
        _, project, split = max(
            candidates,
            key=lambda item: (
                item[0],
                column_remaining[item[2]],
                -split_names.index(item[2]),
                item[1],
            ),
        )
        allocation[(project, split)] += 1
        row_remaining[project] -= 1
        column_remaining[split] -= 1

    result = {name: [] for name in split_names}
    for project, keys in sorted(projects.items()):
        ordered = sorted(
            keys,
            key=lambda value: hashlib.sha256(f"{seed}::{project}::{value}".encode()).hexdigest(),
        )
        offset = 0
        for split in split_names:
            size = allocation[(project, split)]
            result[split].extend(ordered[offset : offset + size])
            offset += size
    return result


def validate_manual_splits(
    splits: dict[str, list[str]], available: dict[str, TargetReference]
) -> tuple[list[TargetReference], dict[str, list[str]]]:
    required = {"train", "validation", "test"}
    if set(splits) != required:
        raise ValueError("Manual dataset must contain train, validation, and test splits")
    flattened = [target for name in ("train", "validation", "test") for target in splits[name]]
    if not flattened or any(not splits[name] for name in required):
        raise ValueError("Manual train, validation, and test splits must all be non-empty")
    if len(flattened) != len(set(flattened)):
        raise ValueError("A function cannot belong to more than one dataset split")
    missing = sorted(set(flattened) - set(available))
    if missing:
        raise ValueError(f"Unknown manual targets: {', '.join(missing[:10])}")
    return [available[key] for key in flattened], {
        name: list(dict.fromkeys(splits[name])) for name in ("train", "validation", "test")
    }


def _allocate_counts(total: int, percentages: DatasetPercentages) -> dict[str, int]:
    names = ("train", "validation", "test")
    values = percentages.model_dump()
    exact = {name: total * values[name] / 100 for name in names}
    counts = {name: int(exact[name]) for name in names}
    remaining = total - sum(counts.values())
    order = sorted(names, key=lambda name: (-(exact[name] % 1), names.index(name)))
    for name in order[:remaining]:
        counts[name] += 1
    positive = [name for name in names if values[name] > 0]
    if total >= len(positive):
        for name in positive:
            if counts[name]:
                continue
            donor = max((candidate for candidate in names if counts[candidate] > 1), key=counts.get)
            counts[donor] -= 1
            counts[name] += 1
    return counts
