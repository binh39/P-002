import hashlib
import random


def split_targets(target_ids: list[str], seed: int = 7) -> dict[str, list[str]]:
    """Create stable, disjoint train/validation/test IDs for one experiment snapshot."""
    unique = list(dict.fromkeys(target_ids))
    ordered = sorted(unique, key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    random.Random(seed).shuffle(ordered)
    count = len(ordered)
    if count < 3:
        return {"train": ordered, "validation": [], "test": []}
    validation_count = max(1, round(count * 0.2))
    test_count = max(1, round(count * 0.2))
    if validation_count + test_count >= count:
        validation_count = test_count = 1
    train_count = count - validation_count - test_count
    return {
        "train": ordered[:train_count],
        "validation": ordered[train_count : train_count + validation_count],
        "test": ordered[train_count + validation_count :],
    }
