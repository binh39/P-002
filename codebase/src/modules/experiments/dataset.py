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
        candidates.sort(
            key=lambda item: (-item.branches, -item.statements, -item.loc, _stable_key(item))
        )
    elif method == SamplingMethod.MOST_STATEMENTS:
        candidates.sort(
            key=lambda item: (-item.statements, -item.branches, -item.loc, _stable_key(item))
        )
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
    """Create stable, disjoint percentage splits for composite target IDs."""
    percentages = percentages or DatasetPercentages()
    unique = {_stable_key(target): target for target in targets}
    ordered = sorted(unique, key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    random.Random(seed).shuffle(ordered)
    counts = _allocate_counts(len(ordered), percentages)
    train_end = counts["train"]
    validation_end = train_end + counts["validation"]
    return {
        "train": ordered[:train_end],
        "validation": ordered[train_end:validation_end],
        "test": ordered[validation_end:],
    }


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
