"""Build bounded repository-local context for one CoverUp target."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from .segment import CodeSegment

TARGET_CONTEXT_SCHEMA = 1
DEFAULT_TARGET_CONTEXT_MAX_CHARS = 6_000
DEFAULT_FAILURE_CONTEXT_MAX_CHARS = 4_000
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


def build_failure_context(
    segment: CodeSegment,
    error: str,
    *,
    project_root: Path | None = None,
    max_chars: int = DEFAULT_FAILURE_CONTEXT_MAX_CHARS,
) -> str:
    """Return bounded source/usage evidence selected by one execution failure.

    Unlike ``build_target_context``, this function is called only after a test
    has failed.  It may retrieve a small number of existing usage examples,
    but never injects the repository test tree into the initial generation.
    """

    if max_chars <= 0:
        return ""
    failure_type = _failure_context_type(error)
    sections = [
        "[FAILURE-TRIGGERED CONTEXT]",
        f"Failure family: {failure_type}",
        _repair_guidance(failure_type),
    ]
    assertion_evidence = _assertion_failure_context(error)
    if assertion_evidence:
        sections.extend(["", "[ASSERTION EVIDENCE]", assertion_evidence])
    clone_pitfall = _clone_pitfall_context(segment, error)
    if clone_pitfall:
        sections.extend(["", "[CLONE/REBUILD PITFALL]", clone_pitfall])
    private_hook = _private_test_hook_context(error)
    if private_hook:
        sections.extend(["", "[PRIVATE TEST HOOK]", private_hook])
    sfs_branches = _sfs_branch_completion_context(segment, error)
    if sfs_branches:
        sections.extend(["", "[SFS BRANCH COMPLETION]", sfs_branches])
    constructor = _enclosing_constructor_context(segment)
    if constructor:
        sections.extend(["", "[ENCLOSING CONSTRUCTOR/PROTOCOL]", constructor])
    root = Path(project_root).resolve() if project_root is not None else None
    exports = _import_export_context(root, error)
    if exports:
        sections.extend(["", "[IMPORT/EXPORT EVIDENCE]", exports])
    usages = _failure_usage_context(root, segment, error)
    if usages:
        sections.extend(["", "[FAILURE-RELEVANT USAGE EXAMPLES]", usages])
    callees = _direct_callee_context(segment)
    if callees:
        sections.extend(["", "[DIRECT CALLEE CONTRACT]", callees])
    sections.extend([
        "",
        "Use only this evidence and the traceback to repair the complete test module. "
        "Do not repeat the same failing setup.",
        "[END FAILURE-TRIGGERED CONTEXT]",
    ])
    rendered = "\n".join(sections)
    if len(rendered) <= max_chars:
        return rendered
    suffix = "\n[FAILURE CONTEXT TRUNCATED]\n[END FAILURE-TRIGGERED CONTEXT]"
    return rendered[: max(0, max_chars - len(suffix))].rstrip() + suffix


def _failure_context_type(error: str) -> str:
    lowered = error.lower()
    if "attributeerror" in lowered or "has no attribute" in lowered:
        return "attribute/protocol"
    if "importerror" in lowered or "modulenotfounderror" in lowered:
        return "import/export"
    if "assertionerror" in lowered or re.search(r"(?m)^E\s+assert\s", error):
        return "assertion/behavior"
    if "typeerror" in lowered:
        return "type/constructor"
    if "filenotfounderror" in lowered or "oserror" in lowered:
        return "filesystem/environment"
    return "execution/setup"


def _repair_guidance(failure_type: str) -> str:
    common = (
        "Repair the root cause, preserve useful assertions, and return the entire test module. "
    )
    if failure_type == "attribute/protocol":
        return common + (
            "Instantiate a real object that satisfies the required protocol or configure the "
            "documented attribute explicitly; inspect constructor and usage evidence before retrying."
        )
    if failure_type == "import/export":
        return common + (
            "Do not invent an import or add a missing dependency. Use the repository's actual export "
            "location, or remove the unnecessary dependency from the test."
        )
    if failure_type == "assertion/behavior":
        return common + (
            "Derive expectations from source behavior. Avoid guessed counts, absolute paths, ordering, "
            "or environment-specific values; assert stable invariants instead. When pytest reports an "
            "Expected regex and Actual message, remember that match= is a regular expression: prefer "
            "re.escape(actual_message) or capture exc_info and assert a stable literal substring."
        )
    if failure_type == "type/constructor":
        return common + "Match the real constructor and argument types shown in the retrieved contract."
    if failure_type == "filesystem/environment":
        return common + (
            "Use tmp_path/monkeypatch and assert repository-defined semantics without depending on cwd."
        )
    return common + "Use the retrieved contracts to replace the invalid setup, not only the assertion."


def _assertion_failure_context(error: str) -> str:
    expected = re.search(r"Expected regex:\s*(['\"])(.*?)\1", error, re.DOTALL)
    actual = re.search(r"Actual message:\s*(['\"])(.*?)\1", error, re.DOTALL)
    if not expected and not actual:
        return ""
    lines = [
        "pytest's match= argument is a regex, not a literal string. Do not guess or normalize "
        "the runtime message's spacing/punctuation."
    ]
    if expected:
        lines.append(f"Failed expected regex: {expected.group(2)!r}")
    if actual:
        lines.append(f"Observed runtime message (exact): {actual.group(2)!r}")
    lines.append(
        "Repair with re.escape(observed_message), a short regex-safe substring, or exc_info plus "
        "a literal assertion on str(exc_info.value)."
    )
    return "\n".join(lines)


_CLONE_PITFALL_SIGNALS = ("_estimator_type", "clone(", "clone_estimator")


def _clone_pitfall_context(segment: CodeSegment, error: str) -> str:
    """Explain an estimator-protocol failure caused by instance attributes lost in clone().

    Many sklearn-style meta-estimators rebuild their wrapped estimator with
    ``sklearn.base.clone()`` (or repeat ``get_params()``-only reconstruction) inside
    ``__init__`` when ``clone_estimator`` is enabled. Attributes set manually on an
    instance the test passes in (e.g. ``obj._estimator_type = "classifier"``) are not
    ``get_params()``-exposed and are silently dropped, so the exact same failure recurs
    on every repair. This hint is injected only when the error and the enclosing
    constructor source match that pattern.
    """

    if "_estimator_type" not in error:
        return ""
    try:
        source = segment.path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(segment.path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return ""
    if not any(signal in source for signal in _CLONE_PITFALL_SIGNALS):
        return ""
    lines = [
        "The wrapped estimator is rebuilt via clone() (or get_params()-only reconstruction) "
        "when clone_estimator is enabled, so attributes set directly on the instance you pass "
        "in (for example `obj._estimator_type = \"classifier\"`) are silently discarded and the "
        "same failure will recur on every rewrite.",
    ]
    lines.append(
        "Do not monkey-patch the instance, and do not rely on the estimator exposing "
        "`_estimator_type`: in the sklearn version this repo runs, no estimator declares that "
        "attribute at class scope, so setting it on an instance is both dropped by clone() and "
        "insufficient. Pass the `scoring` parameter explicitly as a documented string (e.g. "
        "`scoring='accuracy'` or `scoring='r2'`); a non-None `scoring` skips the "
        "`_estimator_type` constructor check entirely. Alternatively set `clone_estimator=False`."
    )
    return "\n".join(lines)


_PRIVATE_TEST_HOOK_RE = re.compile(r"_TESTING_[A-Za-z_]+")


def _private_test_hook_context(error: str) -> str:
    """Warn when a repair probes a private ``_TESTING_`` hook on the target.

    The failing module often invents a private hook (e.g. ``obj._TESTING_INTERRUPT_MODE = True``)
    and expects the code to raise. Such attributes are not part of the public API, so the
    ``pytest.raises(...)`` assertion fails (e.g. "DID NOT RAISE KeyboardInterrupt"); one failing
    test then rejects the entire module, discarding passing coverage. The error string carries the
    traceback, which includes the model's own ``_TESTING_*`` reference, so this fires even though
    the exception itself is unrelated to ``_estimator_type``.
    """

    if not _PRIVATE_TEST_HOOK_RE.search(error):
        return ""
    return (
        "You probed a private `_TESTING_*` attribute (or expected an interrupt) on the target, "
        "which is not part of the real public API. Setting `obj._TESTING_* = ...` and expecting "
        "the code to raise will fail (e.g. 'DID NOT RAISE KeyboardInterrupt'), and that one "
        "failure rejects the entire module, discarding your passing coverage. Remove the private "
        "hook; assert observable public behavior instead (e.g. `fitted`, `k_feature_idx_`, "
        "`subsets_`)."
    )


_SFS_BRANCH_MARKERS = ("k_features", "feature_groups", "floating", "forward")
_SFS_BRANCH_ERROR_RE = re.compile(r"AttributeError|ValueError")


def _sfs_branch_completion_context(segment: CodeSegment, error: str) -> str:
    """Nudge SFS-style meta-estimator repairs to also cover rare feature-search branches.

    From trace analysis of ``SequentialFeatureSelector.fit``, the remaining gap on this
    target is overwhelmingly the *rare* branches, not the constructor error: a repair that
    only fixes the immediate ``ValueError``/``AttributeError`` will restart at the same
    validation branch and never reach the floating-backward loop nor the string
    ``k_features`` modes. This hint fires only for a fit-style method whose source carries
    the SFS kwarg markers and whose error is a validation/attribute failure.
    """

    if not _SFS_BRANCH_ERROR_RE.search(error):
        return ""
    try:
        source = segment.path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(segment.path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return ""
    if not all(marker in source for marker in _SFS_BRANCH_MARKERS):
        return ""
    if segment.name not in {"fit", "fit_transform", "fit_predict"}:
        return ""
    return (
        "Do not stop at fixing just this one validation branch. This target's remaining "
        "coverage is concentrated in rare feature-selection branches, and a repair is more "
        "robust when it exercises all of them in separate test functions:\n"
        "- pass `k_features` as a string too (`'best'` and `'parsimonious'`), not only int/tuple; "
        "`'parsimonious'` flips the internal `is_parsimonious` flag;\n"
        "- run at least one `forward=True, floating=True` fit so the floating-backward loop "
        "(subset re-evaluation, break-on-no-improvement, and accept-on-improvement paths) executes. "
        "The floating *body* is gated: the loop breaks before its body when the current feature "
        "count is within 2 of the target (e.g. `forward=True`, no fixed features, and "
        "`k_features <= 2`). To actually reach the floating loops, use enough columns and a "
        "target that keeps the count above that guard — for example `k_features=3` on an X with "
        "at least 4 columns (so `len(k_idx) - len(fixed_features) > 2` on the way to the target);\n"
        "- optionally set `verbose=1`/`verbose>1` to cover the progress-stderr branches;\n"
        "- cover `fixed_features` and `feature_groups` validation errors (`mixed types`, a name "
        "mapping without a DataFrame, a group that is not a partition).\n"
        "Prefer several small independent `test_*` functions so one failing branch does not "
        "discard coverage from the other branches."
    )


def _enclosing_constructor_context(segment: CodeSegment) -> str:
    try:
        source = segment.path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(segment.path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return ""
    found = _target_node(segment, tree)
    if found is None:
        return ""
    node, _qualname, parents = found
    class_name = next(reversed(parents), "") if parents else ""
    if not class_name and isinstance(node, ast.ClassDef):
        class_name = node.name
    class_node = next(
        (
            candidate
            for candidate, qualname, _ in _qualified_nodes(tree)
            if isinstance(candidate, ast.ClassDef) and qualname == class_name
        ),
        None,
    )
    if class_node is None:
        return ""
    constructor = next(
        (
            child
            for child in class_node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name == "__init__"
        ),
        None,
    )
    if constructor is None:
        bases = ", ".join(ast.unparse(base) for base in class_node.bases) or "object"
        return f"{class_name} inherits {bases}; no local __init__ is defined."
    signature = _format_signature(constructor, f"{class_name}.__init__")
    body = _node_source(source, constructor)
    if len(body) > 900:
        body = body[:900].rstrip() + "\n# constructor truncated"
    return f"{signature}\n{body}"


def _direct_callee_context(segment: CodeSegment) -> str:
    try:
        source = segment.path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(segment.path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return ""
    found = _target_node(segment, tree)
    if found is None:
        return ""
    target_node = found[0]
    called_names = {
        _call_name(node.func)
        for node in ast.walk(target_node)
        if isinstance(node, ast.Call)
    }
    called_names.discard("")
    candidates = []
    for node, qualname, _parents in _qualified_nodes(tree):
        if node is target_node or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in called_names:
            continue
        body = _node_source(source, node)
        candidates.append((qualname, body[:650]))
    return "\n\n".join(
        f"{qualname}:\n{body}" for qualname, body in sorted(candidates)[:1]
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _failure_usage_context(
    project_root: Path | None,
    segment: CodeSegment,
    error: str,
) -> str:
    if project_root is None or not project_root.is_dir():
        return ""
    tests, _fixtures = _collect_test_snippets(project_root, segment)
    error_tokens = _failure_tokens(error)
    scored = []
    for snippet in tests:
        lowered = snippet.source.lower()
        error_score = sum(12 for token in error_tokens if token.lower() in lowered)
        scored.append((
            -(snippet.score + error_score),
            -error_score,
            str(snippet.path),
            getattr(snippet.node, "lineno", 0),
            snippet,
        ))
    error_matches = [item for item in scored if item[1] < 0]
    selected = sorted(error_matches)[:1]
    selected_ids = {(item[2], item[3]) for item in selected}
    positive_matches = [
        item for item in scored
        if item[1] == 0 and (item[2], item[3]) not in selected_ids
    ]
    selected.extend(sorted(positive_matches)[: max(0, 2 - len(selected))])
    if not selected:
        selected = sorted(scored)[:2]
    parts = []
    for _score, negative_error_score, _path, _line, snippet in selected:
        try:
            relative = snippet.path.relative_to(project_root)
        except ValueError:
            relative = snippet.path
        support = _supporting_definitions(snippet)
        source = snippet.source
        if len(source) > 850:
            source = source[:850].rstrip() + "\n# usage truncated"
        kind = "failure/contract example" if negative_error_score < 0 else "valid usage candidate"
        rendered = f"{kind} from {relative.as_posix()}:\n"
        if support:
            rendered += support + "\n\n"
        rendered += source
        parts.append(rendered)
    return "\n\n".join(parts)


def _supporting_definitions(snippet: _Snippet) -> str:
    try:
        source = snippet.path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(snippet.path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return ""
    referenced = {
        node.id for node in ast.walk(snippet.node) if isinstance(node, ast.Name)
    }
    definitions = []
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in referenced:
            continue
        rendered = _node_source(source, node)
        if len(rendered) > 400:
            rendered = rendered[:400].rstrip() + "\n# supporting definition truncated"
        definitions.append(rendered)
    return "\n\n".join(definitions[:2])


def _failure_tokens(error: str) -> set[str]:
    tokens = {
        value
        for value in re.findall(r"[`'\"]([A-Za-z_][A-Za-z0-9_.]{2,})[`'\"]", error)
    }
    tokens.update(re.findall(r"\.[A-Za-z_][A-Za-z0-9_]{2,}", error))
    tokens.update(
        value
        for value in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{4,}\b", error)
        if "_" in value
    )
    return {value.lstrip(".") for value in tokens}


def _import_export_context(project_root: Path | None, error: str) -> str:
    if project_root is None or not project_root.is_dir():
        return ""
    match = re.search(r"cannot import name ['\"]([^'\"]+)['\"]", error, re.IGNORECASE)
    missing_module = re.search(r"No module named ['\"]([^'\"]+)['\"]", error)
    wanted = match.group(1) if match else ""
    if missing_module and not wanted:
        return (
            f"Module {missing_module.group(1)!r} is unavailable in this project environment. "
            "Do not import it in the repaired test unless repository source proves it is required."
        )
    if not wanted:
        return ""
    matches = []
    for path in sorted(project_root.rglob("*.py")):
        if any(part in {".git", ".promptopt-site", "__pycache__"} for part in path.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == wanted:
                matches.append(path)
                break
    if not matches:
        return f"No repository definition named {wanted!r} was found; do not invent this import."
    return "Actual definitions: " + ", ".join(
        path.relative_to(project_root).as_posix() for path in matches[:4]
    )
