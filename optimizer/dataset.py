from __future__ import annotations

import ast
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import dspy


def source_file_to_module_import(source_file: str | Path) -> str:
    """Convert a repository-relative Python source file to a dotted import."""
    path = Path(source_file)
    if path.suffix != ".py":
        raise ValueError(f"Expected a Python source file, got {source_file!s}")
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    if not parts or any(not part.isidentifier() for part in parts):
        raise ValueError(f"Cannot derive a Python import from {source_file!s}")
    return ".".join(parts)


def _qualified_nodes(tree: ast.AST) -> dict[str, ast.AST]:
    found: dict[str, ast.AST] = {}

    def visit(body: list[ast.stmt], prefix: str = "") -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f"{prefix}.{node.name}" if prefix else node.name
                found[qualified] = node
                if isinstance(node, ast.ClassDef):
                    visit(node.body, qualified)

    visit(getattr(tree, "body", []))
    return found


def extract_focal_code(source_path: str | Path, symbol: str) -> str:
    path = Path(source_path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    try:
        node = _qualified_nodes(tree)[symbol]
    except KeyError as exc:
        raise KeyError(f"Symbol {symbol!r} was not found in {path}") from exc
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno])


def build_examples(functions: Iterable[dict[str, Any]]) -> list[dspy.Example]:
    examples = []
    for function in functions:
        payload = dict(function)
        payload["module_path"] = str(payload["module_path"])
        payload["focal_code"] = str(payload["focal_code"])
        payload["existing_tests"] = str(payload.get("existing_tests", ""))
        payload["coverage_feedback"] = str(payload.get("coverage_feedback", ""))
        payload["module_import"] = str(payload.get("module_import", ""))
        payload["target_symbol"] = str(payload.get("target_symbol", ""))
        if "source_path" in payload:
            payload["source_path"] = str(payload["source_path"])
        example = dspy.Example(**payload).with_inputs(
            "module_import",
            "target_symbol",
            "focal_code",
            "existing_tests",
            "coverage_feedback",
        )
        examples.append(example)
    return examples


def load_symbol_examples(
    dataset_path: str | Path,
    source_root: str | Path,
    *,
    split: str | None = None,
    limit: int | None = None,
    harness_module_path: str | Path | None = None,
) -> list[dspy.Example]:
    """Load JSONL symbol targets and materialize focal source for DSPy."""
    dataset = Path(dataset_path)
    root = Path(source_root)
    records: list[dict[str, Any]] = []
    with dataset.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                target = json.loads(line)
                source_path = root / target["source_file"]
                if split is not None and target["split"] != split:
                    continue
                records.append(
                    {
                        "module_path": harness_module_path or source_path,
                        "source_path": source_path,
                        "example_id": f"{target['source_file']}::{target['symbol']}",
                        "symbol": target["symbol"],
                        "module_import": source_file_to_module_import(
                            target["source_file"]
                        ),
                        "target_symbol": target["symbol"],
                        "split": target["split"],
                        "focal_code": extract_focal_code(source_path, target["symbol"]),
                        "existing_tests": "",
                        "coverage_feedback": "",
                    }
                )
            except (KeyError, TypeError, json.JSONDecodeError, SyntaxError) as exc:
                raise ValueError(
                    f"Invalid function target at {dataset}:{line_number}: {exc}"
                ) from exc
            if limit is not None and len(records) >= limit:
                break
    return build_examples(records)


def build_v2_splits(
    dataset_path: str | Path,
    source_root: str | Path,
    *,
    harness_module_path: str | Path | None = None,
) -> tuple[list[dspy.Example], list[dspy.Example], list[dspy.Example]]:
    """Build the fixed 20/10/10 train/validation/held-out protocol for v2."""
    common = {
        "dataset_path": dataset_path,
        "source_root": source_root,
        "harness_module_path": harness_module_path,
    }
    train = load_symbol_examples(**common, split="train", limit=20)
    validation = load_symbol_examples(**common, split="validation", limit=10)
    holdout = load_symbol_examples(**common, split="test", limit=10)
    actual = (len(train), len(validation), len(holdout))
    if actual != (20, 10, 10):
        raise ValueError(
            "v2 requires exactly 20 train, 10 validation, and 10 held-out "
            f"examples; got {actual}"
        )
    return train, validation, holdout
