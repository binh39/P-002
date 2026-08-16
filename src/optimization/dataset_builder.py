"""Rank every function of a set of projects into a benchmark dataset.

The prompt-optimization pipeline consumes a flat JSONL dataset with one row
per symbol:

    {"project": "isort", "source_file": "isort/main.py",
     "symbol": "sort_imports", "split": "train"}

This module builds that dataset statically, without running the projects or
their test suites.  Every function of every project is measured with ``ast``
and then ranked:

1. number of branches, descending;
2. number of statements, descending;
3. number of source lines, descending;
4. deterministic order by project name, source file, then symbol (ascending).

The selected functions are stratified by project.  Every split receives a
project mix proportional to the number of available functions, while ranks
within each project are interleaved across splits so difficulty is not
silently confounded with the split label.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_EXCLUDED_DIRS = frozenset({"_vendored", "externals", "tests", "__pycache__"})
_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclass(frozen=True)
class FunctionInfo:
    """Static metrics of a single function or method."""

    project: str
    source_file: str
    symbol: str
    branches: int
    statements: int
    lines: int
    lineno: int


def count_branches(node: ast.AST) -> int:
    """Count static branch points owned by ``node``.

    Nested function/class bodies are skipped so each function is measured
    independently.  The counted decision points follow coverage.py's branch
    semantics: every ``if`` (including ``elif`` chains), ``while``, ``with``,
    ``assert`` and ternary expression contributes two arcs; every
    ``for``/``async for`` contributes two; ``try`` contributes one per handler
    plus the normal exit; every ``match`` case contributes one; and boolean
    short-circuit operators contribute one per operand.
    """

    total = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _NESTED_SCOPES):
            continue
        if isinstance(
            child,
            (ast.If, ast.While, ast.With, ast.AsyncWith, ast.Assert, ast.IfExp),
        ):
            total += 2
        elif isinstance(child, (ast.For, ast.AsyncFor)):
            total += 2
        elif isinstance(child, ast.Try):
            total += len(child.handlers) + 1
        elif isinstance(child, ast.Match):
            total += max(1, len(child.cases))
        elif isinstance(child, ast.BoolOp):
            total += len(child.values)
        total += count_branches(child)
    return total


def count_statements(node: ast.AST) -> int:
    """Count executable statements owned by ``node``.

    Nested function/class bodies are excluded: their statements belong to the
    nested symbol, matching how coverage.py attributes lines per function.
    """

    total = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _NESTED_SCOPES):
            continue
        if isinstance(child, ast.stmt):
            total += 1
        total += count_statements(child)
    return total


def function_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the number of source lines spanned by ``node``."""

    return node.end_lineno - node.lineno + 1


def _collect_from_tree(
    tree: ast.Module,
    project: str,
    source_file: str,
    result: list[FunctionInfo],
) -> None:
    """Walk ``tree`` and append one ``FunctionInfo`` per def/async def."""

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
                result.append(
                    FunctionInfo(
                        project=project,
                        source_file=source_file,
                        symbol=".".join([*prefix, child.name]),
                        branches=count_branches(child),
                        statements=count_statements(child),
                        lines=function_lines(child),
                        lineno=child.lineno,
                    )
                )
                stack.append((child, [*parents, child]))
            elif isinstance(child, ast.ClassDef):
                stack.append((child, [*parents, child]))
            else:
                stack.append((child, parents))


def collect_project_functions(
    package_dir: Path,
    project: str,
    exclude_dirs: frozenset[str] = _DEFAULT_EXCLUDED_DIRS,
) -> list[FunctionInfo]:
    """Collect every function under ``package_dir`` as a list of metrics."""

    package_dir = Path(package_dir)
    result: list[FunctionInfo] = []
    for path in sorted(package_dir.rglob("*.py")):
        relative = path.relative_to(package_dir)
        if any(part in exclude_dirs for part in relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise ValueError(f"Failed to parse {path}: {exc}") from exc
        source_file = f"{project}/{relative.as_posix()}"
        _collect_from_tree(tree, project, source_file, result)
    return result


def rank_functions(functions: list[FunctionInfo]) -> list[FunctionInfo]:
    """Sort by branch count, then statements, then lines, then identity."""

    return sorted(
        functions,
        key=lambda info: (
            -info.branches,
            -info.statements,
            -info.lines,
            info.project,
            info.source_file,
            info.symbol,
        ),
    )


def assign_splits(
    ranked: list[FunctionInfo],
    *,
    train_limit: int,
    validation_limit: int,
    test_limit: int,
) -> list[dict]:
    """Assign exact split limits while stratifying project and rank."""

    split_limits = {
        "train": train_limit,
        "validation": validation_limit,
        "test": test_limit,
    }
    if any(limit < 0 for limit in split_limits.values()):
        raise ValueError("Split limits cannot be negative")
    project_ranked: dict[str, list[FunctionInfo]] = {}
    for info in ranked:
        project_ranked.setdefault(info.project, []).append(info)
    total_available = len(ranked)
    if not total_available:
        return []

    # Allocate the project x split matrix close to its proportional ideal,
    # with exact split column totals and without exceeding any project size.
    projects = sorted(project_ranked)
    ideal = {
        (project, split): (
            len(project_ranked[project]) * limit / total_available
        )
        for project in projects
        for split, limit in split_limits.items()
    }
    allocation = {
        cell: int(value) for cell, value in ideal.items()
    }
    column_remaining = {
        split: limit - sum(allocation[(project, split)] for project in projects)
        for split, limit in split_limits.items()
    }
    row_remaining = {
        project: len(project_ranked[project]) - sum(
            allocation[(project, split)] for split in split_limits
        )
        for project in projects
    }
    while any(remaining for remaining in column_remaining.values()):
        candidates = [
            (ideal[(project, split)] - allocation[(project, split)], project, split)
            for project in projects
            for split in split_limits
            if column_remaining[split] > 0 and row_remaining[project] > 0
        ]
        if not candidates:
            raise ValueError("Unable to satisfy stratified split limits")
        _, project, split = max(
            candidates,
            key=lambda item: (
                item[0],
                column_remaining[item[2]],
                -list(split_limits).index(item[2]),
                item[1],
            ),
        )
        allocation[(project, split)] += 1
        column_remaining[split] -= 1
        row_remaining[project] -= 1

    assigned: dict[FunctionInfo, str] = {}
    split_order = tuple(split_limits)
    for project in projects:
        counts = {
            split: allocation[(project, split)] for split in split_order
        }
        selected_count = sum(counts.values())
        used = {split: 0 for split in split_order}
        for index, info in enumerate(project_ranked[project][:selected_count], start=1):
            eligible = [split for split in split_order if used[split] < counts[split]]
            split = max(
                eligible,
                key=lambda name: (
                    index * counts[name] / selected_count - used[name],
                    -split_order.index(name),
                ),
            )
            assigned[info] = split
            used[split] += 1

    return [
        {
            "project": info.project,
            "source_file": info.source_file,
            "symbol": info.symbol,
            "split": assigned[info],
        }
        for info in ranked
        if info in assigned
    ]


def build_dataset(
    projects: list[tuple[str, Path]],
    *,
    train_limit: int,
    validation_limit: int,
    test_limit: int,
    global_top: bool = False,
    exclude_dirs: frozenset[str] = _DEFAULT_EXCLUDED_DIRS,
) -> tuple[list[dict], list[FunctionInfo]]:
    """Rank functions and assign project-stratified requested splits.

    Returns ``(target_rows, ranked_functions)``.  ``target_rows`` is exactly
    the JSONL-serializable dataset with the four fields used by the pipeline:
    ``project``, ``source_file``, ``symbol`` and ``split``.
    """

    functions: list[FunctionInfo] = []
    for project, package_dir in projects:
        functions.extend(collect_project_functions(package_dir, project, exclude_dirs))
    ranked = rank_functions(functions)
    requested = train_limit + validation_limit + test_limit
    if len(ranked) < requested:
        raise ValueError(
            f"Only {len(ranked)} functions found but {requested} were requested "
            "(train_limit + validation_limit + test_limit)"
        )
    # Cloud's ``most_branches`` sampling selects the global top-N pool first,
    # then stratifies that fixed pool across splits.  Keep the historical
    # project-quota behavior as the default for existing benchmark datasets.
    assignment_pool = ranked[:requested] if global_top else ranked
    targets = assign_splits(
        assignment_pool,
        train_limit=train_limit,
        validation_limit=validation_limit,
        test_limit=test_limit,
    )
    return targets, ranked
