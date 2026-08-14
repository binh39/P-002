"""Build bounded repository-local context for one CoverUp target."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .segment import CodeSegment

TARGET_CONTEXT_SCHEMA = 1
DEFAULT_TARGET_CONTEXT_MAX_CHARS = 6_000
_MAX_TEST_FILES = 4
_MAX_TEST_SNIPPETS = 4
_MAX_FIXTURE_SNIPPETS = 2


@dataclass(frozen=True)
class _Snippet:
    path: Path
    node: ast.AST
    source: str
    score: int


def _qualified_nodes(tree: ast.AST):
    """Yield definitions together with their lexical qualified names."""

    def visit(node: ast.AST, parents: tuple[str, ...] = ()):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualname = ".".join((*parents, child.name))
                yield child, qualname, parents
                yield from visit(child, (*parents, child.name))
            else:
                yield from visit(child, parents)

    yield from visit(tree)


def _target_node(segment: CodeSegment, tree: ast.AST):
    candidates = list(_qualified_nodes(tree))
    for item in candidates:
        node, qualname, _ = item
        decorators = getattr(node, "decorator_list", ())
        start = min(
            [getattr(node, "lineno", -1), *(item.lineno for item in decorators)]
        )
        if qualname == segment.qualname and start <= segment.begin:
            return item
    for item in candidates:
        node, _, _ = item
        decorators = getattr(node, "decorator_list", ())
        start = min(
            [getattr(node, "lineno", -1), *(item.lineno for item in decorators)]
        )
        end = getattr(node, "end_lineno", getattr(node, "lineno", -1))
        if node.name == segment.name and start <= segment.begin <= end:
            return item
    return None


def _format_signature(node: ast.AST, qualname: str) -> str:
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        return f"class {qualname}({bases})" if bases else f"class {qualname}"
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return qualname
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{prefix} {qualname}({ast.unparse(node.args)}){returns}"


def _contract_context(segment: CodeSegment) -> str:
    try:
        source = segment.path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(segment.path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return f"Target: {segment.qualname}"
    found = _target_node(segment, tree)
    if found is None:
        return f"Target: {segment.qualname}"
    node, qualname, parents = found
    lines = [f"Signature: {_format_signature(node, qualname)}"]
    decorators = getattr(node, "decorator_list", ())
    if decorators:
        lines.append("Decorators: " + ", ".join(f"@{ast.unparse(item)}" for item in decorators))
    docstring = ast.get_docstring(node, clean=True)
    if docstring:
        compact = " ".join(docstring.split())
        lines.append(f"Docstring: {compact[:800]}")
    if parents:
        class_nodes = {
            nested_qualname: nested
            for nested, nested_qualname, _ in _qualified_nodes(tree)
            if isinstance(nested, ast.ClassDef)
        }
        enclosing = []
        for index in range(1, len(parents) + 1):
            parent_name = ".".join(parents[:index])
            parent = class_nodes.get(parent_name)
            if parent is not None:
                bases = ", ".join(ast.unparse(base) for base in parent.bases) or "object"
                enclosing.append(f"{parent_name}({bases})")
        if enclosing:
            lines.append("Enclosing classes: " + ", ".join(enclosing))
    return "\n".join(lines)


def _test_tokens(segment: CodeSegment) -> set[str]:
    module = segment.path.stem
    names = {segment.name, module}
    names.update(part for part in segment.qualname.split(".") if len(part) >= 3)
    return {name for name in names if len(name) >= 3}


def _node_source(source: str, node: ast.AST) -> str:
    lines = source.splitlines()
    start = max(0, getattr(node, "lineno", 1) - 1)
    end = getattr(node, "end_lineno", start + 1)
    return "\n".join(lines[start:end]).strip()


def _is_fixture(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
        "fixture" in ast.unparse(decorator) for decorator in node.decorator_list
    )


def _collect_test_snippets(tests_dir: Path, segment: CodeSegment) -> tuple[list[_Snippet], list[_Snippet]]:
    tokens = _test_tokens(segment)
    tests: list[_Snippet] = []
    fixtures: list[_Snippet] = []
    for path in sorted(tests_dir.rglob("*.py")):
        if any(part in {".git", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        lowered = source.lower()
        file_score = sum(3 for token in tokens if token.lower() in lowered)
        if not file_score and path.name != "conftest.py":
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            snippet_source = _node_source(source, node)
            snippet_lower = snippet_source.lower()
            score = file_score + sum(6 for token in tokens if token.lower() in snippet_lower)
            snippet = _Snippet(path, node, snippet_source, score)
            if _is_fixture(node):
                fixtures.append(snippet)
            elif node.name.startswith("test_") and score > 0:
                tests.append(snippet)
    tests.sort(key=lambda value: (-value.score, str(value.path), value.node.lineno))
    fixtures.sort(key=lambda value: (-value.score, str(value.path), value.node.lineno))
    return tests, fixtures


def _referenced_fixtures(tests: list[_Snippet], fixtures: list[_Snippet]) -> list[_Snippet]:
    argument_names = {
        argument.arg
        for snippet in tests
        if isinstance(snippet.node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for argument in (
            *snippet.node.args.posonlyargs,
            *snippet.node.args.args,
            *snippet.node.args.kwonlyargs,
        )
    }
    selected = [
        fixture
        for fixture in fixtures
        if isinstance(fixture.node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and fixture.node.name in argument_names
    ]
    return selected[:_MAX_FIXTURE_SNIPPETS]


def _test_context(tests_dir: Path | None, segment: CodeSegment) -> str:
    if tests_dir is None or not tests_dir.is_dir():
        return ""
    tests, fixtures = _collect_test_snippets(tests_dir, segment)
    selected_tests = tests[:_MAX_TEST_SNIPPETS]
    selected_fixtures = _referenced_fixtures(selected_tests, fixtures)
    snippets = [*selected_tests, *selected_fixtures]
    if not snippets:
        return ""
    distinct_files: list[Path] = []
    parts = []
    for snippet in snippets:
        if snippet.path not in distinct_files:
            if len(distinct_files) >= _MAX_TEST_FILES:
                continue
            distinct_files.append(snippet.path)
        relative = snippet.path.relative_to(tests_dir)
        kind = "fixture" if _is_fixture(snippet.node) else "test"
        parts.append(f"{kind} from {relative.as_posix()}:\n{snippet.source}")
    return "\n\n".join(parts)


def build_target_context(
    segment: CodeSegment,
    tests_dir: Path | None = None,
    max_chars: int = DEFAULT_TARGET_CONTEXT_MAX_CHARS,
) -> str:
    """Return bounded target contract and repository test patterns."""
    if max_chars <= 0:
        return ""
    sections = ["[TARGET CONTRACT]", _contract_context(segment)]
    tests = _test_context(tests_dir, segment)
    if tests:
        sections.extend(["", "[RELEVANT EXISTING TESTS AND FIXTURES]", tests])
    sections.extend([
        "",
        "Use this repository-local context as guidance only. Do not modify existing tests.",
        "[END TARGET CONTEXT]",
    ])
    rendered = "\n".join(sections)
    if len(rendered) <= max_chars:
        return rendered
    suffix = "\n[CONTEXT TRUNCATED]\n[END TARGET CONTEXT]"
    return rendered[: max(0, max_chars - len(suffix))].rstrip() + suffix
