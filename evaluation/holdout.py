from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _qualified_functions(tree: ast.Module) -> Iterable[tuple[str, ast.AST]]:
    def visit(body: list[ast.stmt], prefix: str = ""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}.{node.name}" if prefix else node.name
                yield name, node
            elif isinstance(node, ast.ClassDef):
                class_name = f"{prefix}.{node.name}" if prefix else node.name
                yield from visit(node.body, class_name)

    yield from visit(tree.body)


def _branch_count(node: ast.AST) -> int:
    branch_nodes = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.IfExp,
        ast.BoolOp,
        ast.Match,
    )
    return sum(isinstance(child, branch_nodes) for child in ast.walk(node))


def select_fresh_holdout(
    source_root: str | Path,
    excluded_ids: set[str],
    *,
    count: int = 10,
    seed: str = "v-final-import-contract-v2",
) -> list[dict[str, str]]:
    """Select an unseen, deterministic holdout without inspecting test outcomes."""
    root = Path(source_root)
    candidates: list[tuple[str, dict[str, str]]] = []
    for source_path in sorted((root / "isort").rglob("*.py")):
        relative = source_path.relative_to(root).as_posix()
        tree = ast.parse(
            source_path.read_text(encoding="utf-8"),
            filename=str(source_path),
        )
        for symbol, node in _qualified_functions(tree):
            example_id = f"{relative}::{symbol}"
            line_count = int(node.end_lineno or node.lineno) - node.lineno + 1
            if (
                example_id in excluded_ids
                or not 8 <= line_count <= 80
                or _branch_count(node) < 2
            ):
                continue
            rank = hashlib.sha256(f"{seed}:{example_id}".encode()).hexdigest()
            candidates.append(
                (
                    rank,
                    {
                        "project": "isort",
                        "source_file": relative,
                        "symbol": symbol,
                        "split": "test",
                    },
                )
            )
    selected = [record for _, record in sorted(candidates)[:count]]
    if len(selected) != count:
        raise ValueError(
            f"Fresh holdout requires {count} eligible symbols; got {len(selected)}"
        )
    return selected


def build_corrected_protocol(
    original_dataset: str | Path,
    source_root: str | Path,
) -> list[dict[str, Any]]:
    """Keep train/validation fixed and replace the exposed held-out split."""
    records = [
        json.loads(line)
        for line in Path(original_dataset).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    train = [record for record in records if record["split"] == "train"][:20]
    validation = [
        record for record in records if record["split"] == "validation"
    ][:10]
    excluded = {
        f"{record['source_file']}::{record['symbol']}" for record in records
    }
    holdout = select_fresh_holdout(source_root, excluded)
    return [*train, *validation, *holdout]


def write_protocol(records: Iterable[dict[str, Any]], output: str | Path) -> None:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "".join(
            json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
