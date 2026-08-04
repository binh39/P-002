from __future__ import annotations

import ast
import difflib
import re
import shlex
import shutil
import subprocess
import uuid
from pathlib import Path

from .package import add_distribution_metadata
from .workspace import docker_mount, temporary_workspace

_STATUS_RE = re.compile(
    r"(?P<location>[^:\n]*?:(?P<line>\d+)(?::\d+)?)[^\n]*?:\s*"
    r"(?P<status>killed|survived)\b",
    re.IGNORECASE,
)
_PROGRESS_RE = re.compile(
    r"(?P<done>\d+)/(?P<total>\d+)\s+"
    r"🎉\s*(?P<killed>\d+).*?🙁\s*(?P<survived>\d+)",
)
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_IDS_RE = re.compile(
    r"^MUTMUT_(?P<status>KILLED|SURVIVED|TIMEOUT|SUSPICIOUS)_IDS="
    r"(?P<ids>[^\r\n]*)$",
    re.MULTILINE,
)


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


def symbol_line_span(source_file: Path, symbol: str) -> tuple[int, int]:
    source = source_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_file))
    try:
        node = _qualified_nodes(tree)[symbol]
    except KeyError as exc:
        raise KeyError(f"Symbol {symbol!r} was not found in {source_file}") from exc
    return node.lineno, node.end_lineno


def _write_symbol_patch(
    source_file: Path,
    symbol: str,
    patch_file: Path,
    *,
    patch_path: str,
) -> None:
    start_line, end_line = symbol_line_span(source_file, symbol)
    source = source_file.read_text(encoding="utf-8")
    original = source.splitlines(keepends=True)
    modified = list(original)
    for index in range(start_line - 1, end_line):
        line = modified[index]
        newline = "\n" if line.endswith("\n") else ""
        modified[index] = line.removesuffix("\n") + " " + newline
    patch = "".join(
        difflib.unified_diff(
            original,
            modified,
            fromfile=patch_path,
            tofile=patch_path,
            n=0,
        )
    )
    patch_file.write_text(patch, encoding="utf-8")


def parse_mutmut_results(output: str) -> tuple[float, list[int]]:
    """Parse mutmut's text report without depending on terminal decorations."""
    output = _ANSI_RE.sub("", output)
    status_counts: dict[str, int] = {}
    for match in _IDS_RE.finditer(output):
        status_counts[match.group("status")] = len(match.group("ids").split())
    if status_counts:
        killed = status_counts.get("KILLED", 0)
        total = sum(status_counts.values())
        return (killed / total if total else 0.0), []

    killed = 0
    survived: list[int] = []
    for match in _STATUS_RE.finditer(output):
        if match.group("status").lower() == "killed":
            killed += 1
        else:
            survived.append(int(match.group("line")))
    total = killed + len(survived)
    if total:
        return killed / total, sorted(set(survived))

    summaries = list(_PROGRESS_RE.finditer(output))
    if summaries:
        summary = summaries[-1]
        total = int(summary.group("total"))
        killed = int(summary.group("killed"))
        return (killed / total if total else 0.0), []
    return 0.0, []


def run_mutation_testing(
    module_path: str | Path,
    test_code: str,
    *,
    mutation_target: str | Path | None = None,
    mutation_symbol: str | None = None,
    timeout: int = 300,
    image: str = "testgen-sandbox:latest",
) -> tuple[float, list[int]]:
    """Run mutmut against a disposable source copy inside the Docker sandbox."""
    module = Path(module_path).resolve()
    if not module.exists():
        raise FileNotFoundError(f"Mutation target does not exist: {module}")

    run_id = uuid.uuid4().hex[:8]
    with temporary_workspace(prefix=f"testgen_mutation_{run_id}_") as temp:
        workspace = Path(temp)
        copied = workspace / module.name
        if module.is_dir():
            shutil.copytree(module, copied)
            add_distribution_metadata(module, workspace)
        else:
            shutil.copy2(module, copied)
        test_file = workspace / f"test_generated_{run_id}.py"
        test_file.write_text(test_code, encoding="utf-8")

        selected_target = module if mutation_target is None else Path(mutation_target).resolve()
        if module.is_dir():
            try:
                relative_target = selected_target.relative_to(module)
            except ValueError as exc:
                raise ValueError(
                    f"Mutation target {selected_target} is outside module {module}"
                ) from exc
            target_path = Path("/work") / copied.name / relative_target
        elif selected_target != module:
            raise ValueError("A file module can only mutate that same file")
        else:
            target_path = Path("/work") / copied.name
        target = shlex.quote(target_path.as_posix())
        tests = shlex.quote(f"/work/{test_file.name}")
        patch_option = ""
        if mutation_symbol:
            if not selected_target.is_file():
                raise ValueError("A mutation symbol requires a focal source file")
            patch_file = workspace / "mutation.patch"
            _write_symbol_patch(
                selected_target,
                mutation_symbol,
                patch_file,
                patch_path=target_path.as_posix(),
            )
            patch_option = (
                f" --use-patch-file {shlex.quote('/work/mutation.patch')}"
            )
        script = (
            f"mutmut run --paths-to-mutate {target} --tests-dir {tests}"
            f"{patch_option} --simple-output --no-progress; "
            "echo MUTMUT_KILLED_IDS=$(mutmut result-ids killed); "
            "echo MUTMUT_SURVIVED_IDS=$(mutmut result-ids survived); "
            "echo MUTMUT_TIMEOUT_IDS=$(mutmut result-ids timeout); "
            "echo MUTMUT_SUSPICIOUS_IDS=$(mutmut result-ids suspicious)"
        )
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "256",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,nosuid,size=128m",
                *docker_mount(workspace, "/work", read_only=False),
                "-w",
                "/work",
                image,
                "sh",
                "-c",
                script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        score, surviving = parse_mutmut_results(result.stdout)
        if not score and not surviving and result.returncode not in (0, 1):
            error = (result.stderr or result.stdout)[-4000:]
            raise RuntimeError(f"mutmut failed with status {result.returncode}: {error}")
        return score, surviving
