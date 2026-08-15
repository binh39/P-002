"""Build a deterministic, failure-stratified benchmark without model calls.

The strata in this module are static challenge proxies.  They deliberately do
not use coverage scores or generated-test outcomes, so a new holdout can be
selected and frozen without evaluating it first.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .dataset_builder import FunctionInfo, count_branches, count_statements, function_lines

FAILURE_STRATA = (
    "branch_heavy",
    "statement_heavy",
    "exception_paths",
    "fixture_mock_dependent",
    "stateful_method",
    "async_io",
    "easy_regression",
)

_EXCLUDED_DIRS = frozenset({"_vendored", "externals", "tests", "__pycache__"})
_IO_ROOTS = frozenset({
    "aiohttp",
    "asyncio",
    "httpx",
    "io",
    "os",
    "pathlib",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "tempfile",
    "urllib",
})
_IO_CALLS = frozenset({
    "open",
    "read",
    "read_bytes",
    "read_text",
    "recv",
    "send",
    "write",
    "write_bytes",
    "write_text",
})
_DEPENDENCY_CALLS = frozenset({
    "chdir",
    "getenv",
    "import_module",
    "mock",
    "monkeypatch",
    "patch",
    "popen",
    "run",
})


@dataclass(frozen=True, slots=True)
class TargetProfile:
    """Static benchmark metadata for one function or method."""

    info: FunctionInfo
    strata: tuple[str, ...]
    difficulty_band: str
    structural_fingerprint: str

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.info.project, self.info.source_file, self.info.symbol)

    def as_dict(self, split: str | None = None) -> dict[str, object]:
        result: dict[str, object] = {
            "project": self.info.project,
            "source_file": self.info.source_file,
            "symbol": self.info.symbol,
            "branches": self.info.branches,
            "statements": self.info.statements,
            "lines": self.info.lines,
            "lineno": self.info.lineno,
            "strata": list(self.strata),
            "difficulty_band": self.difficulty_band,
            "structural_fingerprint": self.structural_fingerprint,
        }
        if split is not None:
            result["split"] = split
        return result


def load_dataset_identities(paths: Iterable[Path]) -> set[tuple[str, str, str]]:
    """Load target identities from existing JSONL datasets."""

    identities: set[tuple[str, str, str]] = set()
    for path in paths:
        with Path(path).open(encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    identity = (
                        str(row["project"]),
                        str(row["source_file"]),
                        str(row["symbol"]),
                    )
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(f"Invalid dataset row at {path}:{line_number}") from exc
                identities.add(identity)
    return identities


def collect_failure_profiles(
    package_dir: Path,
    project: str,
    exclude_dirs: frozenset[str] = _EXCLUDED_DIRS,
) -> list[TargetProfile]:
    """Collect static profiles and project-relative difficulty bands."""

    nodes: list[tuple[FunctionInfo, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    package_dir = Path(package_dir)
    for path in sorted(package_dir.rglob("*.py")):
        relative = path.relative_to(package_dir)
        if any(part in exclude_dirs for part in relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise ValueError(f"Failed to parse {path}: {exc}") from exc
        source_file = f"{project}/{relative.as_posix()}"
        _collect_nodes(tree, project, source_file, nodes)

    if not nodes:
        return []
    branch_threshold = max(4, _upper_quartile([info.branches for info, _ in nodes]))
    statement_threshold = max(8, _upper_quartile([info.statements for info, _ in nodes]))
    complexity = sorted(_complexity(info) for info, _ in nodes)
    lower_threshold = _percentile(complexity, 1 / 3)
    upper_threshold = _percentile(complexity, 2 / 3)

    profiles = []
    for info, node in nodes:
        profile_strata = _classify_node(
            info,
            node,
            branch_threshold=branch_threshold,
            statement_threshold=statement_threshold,
        )
        score = _complexity(info)
        if score <= lower_threshold:
            band = "easy"
        elif score >= upper_threshold:
            band = "hard"
        else:
            band = "medium"
        profiles.append(
            TargetProfile(
                info=info,
                strata=profile_strata,
                difficulty_band=band,
                structural_fingerprint=_structural_fingerprint(node),
            )
        )
    return sorted(profiles, key=lambda profile: profile.identity)


def build_failure_stratified_dataset(
    projects: list[tuple[str, Path]],
    *,
    train_per_project: int,
    validation_per_project: int,
    test_per_project: int,
    excluded_identities: set[tuple[str, str, str]] | None = None,
) -> tuple[list[dict[str, str]], list[TargetProfile], dict[str, object]]:
    """Select exact project-balanced splits while maximizing strata diversity."""

    quotas = {
        "train": train_per_project,
        "validation": validation_per_project,
        "test": test_per_project,
    }
    if any(value < 1 for value in quotas.values()):
        raise ValueError("Every per-project split quota must be at least 1")

    profiles_by_project = {
        project: collect_failure_profiles(package_dir, project)
        for project, package_dir in projects
    }
    excluded = set(excluded_identities or set())
    fingerprint_by_identity = {
        profile.identity: profile.structural_fingerprint
        for profiles in profiles_by_project.values()
        for profile in profiles
    }
    excluded_fingerprints = {
        fingerprint_by_identity[identity]
        for identity in excluded
        if identity in fingerprint_by_identity
    }
    available = {
        project: [
            profile
            for profile in profiles
            if profile.identity not in excluded
            and profile.structural_fingerprint not in excluded_fingerprints
        ]
        for project, profiles in profiles_by_project.items()
    }
    required = sum(quotas.values())
    for project, profiles in available.items():
        unique_fingerprints = {profile.structural_fingerprint for profile in profiles}
        if len(unique_fingerprints) < required:
            raise ValueError(
                f"Project {project} only has {len(unique_fingerprints)} eligible unique "
                f"profiles but {required} are required"
            )

    selected: list[tuple[str, TargetProfile]] = []
    used_fingerprints = set(excluded_fingerprints)
    split_strata = {split: Counter() for split in quotas}
    split_bands = {split: Counter() for split in quotas}
    availability = Counter(
        stratum
        for profiles in available.values()
        for profile in profiles
        for stratum in profile.strata
        if stratum in FAILURE_STRATA
    )

    # Reserve the locked test set first using static features only.  Validation
    # and train then receive their own independent diversity pass.
    ordered_projects = sorted(projects)
    difficulty_cycle = ("easy", "medium", "hard", "medium")
    for split in ("test", "validation", "train"):
        for round_index in range(quotas[split]):
            for project_index, (project, _package_dir) in enumerate(ordered_projects):
                candidates = [
                    profile
                    for profile in available[project]
                    if profile.structural_fingerprint not in used_fingerprints
                ]
                if not candidates:
                    raise ValueError(f"No eligible profile remains for {project}/{split}")
                desired_band = difficulty_cycle[
                    (project_index + round_index) % len(difficulty_cycle)
                ]
                band_candidates = [
                    profile
                    for profile in candidates
                    if profile.difficulty_band == desired_band
                ]
                chosen = min(
                    band_candidates or candidates,
                    key=lambda profile: _selection_key(
                        profile,
                        split_strata[split],
                        split_bands[split],
                        availability,
                    ),
                )
                selected.append((split, chosen))
                used_fingerprints.add(chosen.structural_fingerprint)
                split_strata[split].update(chosen.strata)
                split_bands[split].update([chosen.difficulty_band])

    rows = [
        {
            "project": profile.info.project,
            "source_file": profile.info.source_file,
            "symbol": profile.info.symbol,
            "split": split,
        }
        for split, profile in sorted(
            selected,
            key=lambda item: (
                ("train", "validation", "test").index(item[0]),
                item[1].info.project,
                item[1].info.source_file,
                item[1].info.symbol,
            ),
        )
    ]
    selected_profiles = [profile for _split, profile in selected]
    split_by_identity = {profile.identity: split for split, profile in selected}
    audit = {
        "selection_kind": "static_failure_stratified_v1",
        "excluded_identity_count": len(excluded),
        "excluded_structural_fingerprint_count": len(excluded_fingerprints),
        "eligible_by_project": {
            project: len(profiles) for project, profiles in sorted(available.items())
        },
        "split_counts": dict(Counter(row["split"] for row in rows)),
        "project_split_counts": {
            f"{project}/{split}": sum(
                row["project"] == project and row["split"] == split for row in rows
            )
            for project, _path in sorted(projects)
            for split in quotas
        },
        "strata_by_split": {
            split: dict(sorted(counts.items()))
            for split, counts in split_strata.items()
        },
        "difficulty_by_split": {
            split: dict(sorted(counts.items()))
            for split, counts in split_bands.items()
        },
        "source_universe_digest": _digest_lines(
            f"{'|'.join(profile.identity)}|{profile.structural_fingerprint}"
            for profiles in profiles_by_project.values()
            for profile in profiles
        ),
        "profiles": [
            profile.as_dict(split_by_identity[profile.identity])
            for profile in sorted(selected_profiles, key=lambda item: item.identity)
        ],
    }
    return rows, selected_profiles, audit


def dataset_bytes(rows: list[dict[str, str]]) -> bytes:
    """Serialize rows canonically for stable benchmark hashing."""

    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    ).encode()


def dataset_digest(rows: list[dict[str, str]], split: str | None = None) -> str:
    """Return a SHA-256 for the complete dataset or one split."""

    selected = rows if split is None else [row for row in rows if row["split"] == split]
    return hashlib.sha256(dataset_bytes(selected)).hexdigest()


def _collect_nodes(
    tree: ast.Module,
    project: str,
    source_file: str,
    result: list[tuple[FunctionInfo, ast.FunctionDef | ast.AsyncFunctionDef]],
) -> None:
    stack: list[tuple[ast.AST, list[ast.AST]]] = [(tree, [])]
    while stack:
        node, parents = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = [
                    parent.name
                    for parent in parents
                    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                ]
                info = FunctionInfo(
                    project=project,
                    source_file=source_file,
                    symbol=".".join([*prefix, child.name]),
                    branches=count_branches(child),
                    statements=count_statements(child),
                    lines=function_lines(child),
                    lineno=child.lineno,
                )
                result.append((info, child))
                stack.append((child, [*parents, child]))
            elif isinstance(child, ast.ClassDef):
                stack.append((child, [*parents, child]))
            else:
                stack.append((child, parents))


def _classify_node(
    info: FunctionInfo,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    branch_threshold: int,
    statement_threshold: int,
) -> tuple[str, ...]:
    strata: set[str] = set()
    descendants = list(ast.walk(node))
    calls = [_call_parts(item.func) for item in descendants if isinstance(item, ast.Call)]
    call_roots = {parts[0] for parts in calls if parts}
    call_names = {parts[-1] for parts in calls if parts}

    if info.branches >= branch_threshold:
        strata.add("branch_heavy")
    if info.statements >= statement_threshold:
        strata.add("statement_heavy")
    if any(isinstance(item, (ast.Try, ast.Raise, ast.Assert)) for item in descendants):
        strata.add("exception_paths")
    is_async = isinstance(node, ast.AsyncFunctionDef) or any(
        isinstance(item, (ast.Await, ast.AsyncFor, ast.AsyncWith, ast.Yield, ast.YieldFrom))
        for item in descendants
    )
    has_io = bool(call_roots & _IO_ROOTS or call_names & _IO_CALLS)
    if is_async or has_io:
        strata.add("async_io")
    if (
        call_roots & _IO_ROOTS
        or call_names & _DEPENDENCY_CALLS
        or _has_environment_access(descendants)
    ):
        strata.add("fixture_mock_dependent")
    if "." in info.symbol and _has_state_access(descendants):
        strata.add("stateful_method")
    if info.branches <= 2 and info.statements <= 8 and not strata:
        strata.add("easy_regression")
    if not strata:
        strata.add("general_logic")
    return tuple(sorted(strata))


def _selection_key(
    profile: TargetProfile,
    split_counts: Counter[str],
    band_counts: Counter[str],
    availability: Counter[str],
) -> tuple[float, int, int, int, tuple[str, str, str]]:
    desired = [stratum for stratum in profile.strata if stratum in FAILURE_STRATA]
    stratum_value = sum(
        (8.0 if split_counts[stratum] == 0 else 1.0 / (split_counts[stratum] + 1))
        / max(1, availability[stratum])
        for stratum in desired
    )
    band_value = 3.0 if band_counts[profile.difficulty_band] == 0 else 0.0
    # ``min`` chooses the largest diversity value, then the richer profile,
    # then a deterministic harder-first identity tie-break.
    return (
        -(stratum_value + band_value),
        -len(desired),
        -profile.info.branches,
        -profile.info.statements,
        profile.identity,
    )


def _call_parts(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))


def _has_state_access(nodes: list[ast.AST]) -> bool:
    for node in nodes:
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name) and current.id in {"self", "cls"}:
            return True
    return False


def _has_environment_access(nodes: list[ast.AST]) -> bool:
    for node in nodes:
        if not isinstance(node, ast.Attribute):
            continue
        parts = _call_parts(node)
        if parts[:2] in {("os", "environ"), ("sys", "modules"), ("sys", "path")}:
            return True
    return False


def _structural_fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    normalized = copy.deepcopy(node)
    normalized.name = "<function>"
    if (
        normalized.body
        and isinstance(normalized.body[0], ast.Expr)
        and isinstance(normalized.body[0].value, ast.Constant)
        and isinstance(normalized.body[0].value.value, str)
    ):
        normalized.body = normalized.body[1:]
    dumped = ast.dump(normalized, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(dumped.encode()).hexdigest()[:20]


def _complexity(info: FunctionInfo) -> int:
    return info.branches * 2 + info.statements


def _upper_quartile(values: list[int]) -> int:
    return _percentile(sorted(values), 0.75)


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    index = min(len(values) - 1, max(0, math.ceil(fraction * len(values)) - 1))
    return values[index]


def _digest_lines(lines: Iterable[str]) -> str:
    payload = "\n".join(sorted(lines)).encode()
    return hashlib.sha256(payload).hexdigest()
