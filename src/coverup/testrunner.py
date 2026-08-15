import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from .utils import subprocess_run


@dataclass(frozen=True)
class SalvagedTestCoverage:
    test: str
    coverage: dict
    pruned_failures: int


def _generated_test_failure_line(error: str) -> int | None:
    matches = re.findall(r"tmp_test_[^:\r\n]*\.py:(\d+)(?::|\s)", error)
    return int(matches[-1]) if matches else None


def _has_meaningful_assertion(statements: list[ast.stmt]) -> bool:
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node, ast.Assert):
                return True
            if not isinstance(node, (ast.With, ast.AsyncWith)):
                continue
            for item in node.items:
                context = item.context_expr
                if not isinstance(context, ast.Call):
                    continue
                function = context.func
                if (
                    isinstance(function, ast.Attribute)
                    and function.attr in {"raises", "warns"}
                ):
                    return True
    return False


def _test_functions_with_parents(tree: ast.AST) -> list[tuple[ast.AST, ast.AST]]:
    found: list[tuple[ast.AST, ast.AST]] = []

    def visit(parent: ast.AST) -> None:
        for child in ast.iter_child_nodes(parent):
            if (
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name.startswith("test")
            ):
                found.append((child, parent))
            visit(child)

    visit(tree)
    return found


def _names_with_context(statement: ast.AST, context: type[ast.expr_context]) -> set[str]:
    return {
        node.id
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and isinstance(node.ctx, context)
    }


def _mutated_receiver_names(statement: ast.AST) -> set[str]:
    receivers = set()
    for node in ast.walk(statement):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = node.func.value
        if isinstance(receiver, ast.Name) and receiver.id not in {"pytest"}:
            receivers.add(receiver.id)
    return receivers


def truncate_failing_test_module(test: str, error: str) -> str | None:
    """Remove one failing scenario and statements that depend on its invalid value."""

    failure_line = _generated_test_failure_line(error)
    if failure_line is None:
        return None
    try:
        tree = ast.parse(test)
    except SyntaxError:
        return None
    matches = [
        (node, parent)
        for node, parent in _test_functions_with_parents(tree)
        if node.lineno <= failure_line <= (node.end_lineno or node.lineno)
    ]
    if not matches:
        return None
    function, parent = min(
        matches,
        key=lambda item: (item[0].end_lineno or item[0].lineno) - item[0].lineno,
    )
    failing_statement = next(
        (
            statement
            for statement in function.body
            if statement.lineno <= failure_line <= (
                statement.end_lineno or statement.lineno
            )
        ),
        None,
    )
    if failing_statement is None:
        return None
    failing_index = function.body.index(failing_statement)
    retained = list(function.body[:failing_index])
    poisoned = _names_with_context(failing_statement, ast.Store)
    if not poisoned:
        poisoned = _mutated_receiver_names(failing_statement)
    for statement in function.body[failing_index + 1:]:
        assigned = _names_with_context(statement, ast.Store)
        loaded = _names_with_context(statement, ast.Load)
        if loaded & poisoned:
            poisoned.update(assigned)
            continue
        retained.append(statement)
        poisoned.difference_update(assigned)
    if _has_meaningful_assertion(retained):
        function.body = retained
    else:
        body = getattr(parent, "body", None)
        if not isinstance(body, list):
            return None
        parent.body = [statement for statement in body if statement is not function]
    ast.fix_missing_locations(tree)
    candidate = ast.unparse(tree).strip() + "\n"
    return candidate if candidate.strip() and candidate != test else None


async def salvage_test_coverage(
    *,
    test: str,
    error: str,
    tests_dir: Path,
    pytest_args: str = "",
    log_write=None,
    isolate_tests: bool = False,
    branch_coverage: bool = True,
    max_prunes: int = 8,
) -> SalvagedTestCoverage | None:
    """Iteratively prune failing test suffixes and verify the final whole module."""

    candidate = test
    current_error = error
    for pruned in range(1, max_prunes + 1):
        candidate = truncate_failing_test_module(candidate, current_error)
        if candidate is None:
            return None
        try:
            coverage = await measure_test_coverage(
                test=candidate,
                tests_dir=tests_dir,
                pytest_args=pytest_args,
                log_write=log_write,
                isolate_tests=isolate_tests,
                branch_coverage=branch_coverage,
            )
        except subprocess.CalledProcessError as exc:
            current_error = str(exc.stdout, "UTF-8", errors="ignore")
            continue
        except subprocess.TimeoutExpired:
            return None
        return SalvagedTestCoverage(
            test=(
                "# Salvaged from a generated module after removing failing suffixes.\n"
                + candidate
            ),
            coverage=coverage,
            pruned_failures=pruned,
        )
    return None


def _unsupported_isolate_option(output: bytes | None) -> bool:
    return bool(output and b'unrecognized arguments: --isolate' in output)


async def measure_test_coverage(*, test: str, tests_dir: Path, pytest_args='',
                                log_write=None, isolate_tests=False, branch_coverage=True):
    """Runs a given test and returns the coverage obtained."""
    test_fd, test_name = tempfile.mkstemp(prefix="tmp_test_", suffix='.py', dir=str(tests_dir))
    os.close(test_fd)

    try:
        Path(test_name).write_text(test, encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as j:
            try:
                # -qq to cut down on tokens
                command = [sys.executable, '-X', 'utf8', '-m', 'slipcover',  *(('--branch',) if branch_coverage else ()),
                           '--json', '--out', j.name,
                           '-m', 'pytest', *pytest_args.split(),
                           '-qq', '-x', '--disable-warnings', test_name]

                p = await subprocess_run(command, check=True, timeout=120)

                if log_write:
                    log_write(str(p.stdout, 'UTF-8', errors='ignore'))

                # not checking for JSON errors here because if pytest aborts, its RC ought to be !=0
                cov = json.load(j)
            finally:
                j.close()
                try:
                    os.unlink(j.name)
                except FileNotFoundError:
                    pass
    finally:
        try:
            os.unlink(test_name)
        except FileNotFoundError:
            pass

    return cov


def measure_suite_coverage(*, tests_dir: Path, source_dir: Path | None, pytest_args='',
                           trace=None, isolate_tests=False, branch_coverage=True):
    """Runs an entire test suite and returns the coverage obtained."""

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as j:
        try:
            command = [sys.executable,
                     '-X', 'utf8',
                     '-m', 'slipcover',
                         *(('--source', source_dir) if source_dir else ()),
                         *(('--branch',) if branch_coverage else ()),
                         '--json', '--out', j.name,
                     '-m', 'pytest', *pytest_args.split(),
                         '--disable-warnings', '-x', tests_dir]

            if trace:
                trace(command)
            p = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if p.returncode not in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
                if trace:
                    trace(f"tests rc={p.returncode}\n" + str(p.stdout, 'utf-8'))
                p.check_returncode()

            try:
                return json.load(j)
            except json.decoder.JSONDecodeError:
                # The JSON is broken, so pytest's execution likely aborted (e.g. a Python unhandled exception).
                p.check_returncode() # this will almost certainly raise an exception. If not, we do it ourselves:
                raise subprocess.CalledProcessError(p.returncode, command, output=p.stdout)
        finally:
            j.close()

            try:
                os.unlink(j.name)
            except FileNotFoundError:
                pass
