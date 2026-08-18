from pathlib import Path
import tempfile
import subprocess
import pytest
import typing as T
import sys
import json
import os
from .utils import subprocess_run


def _test_python() -> str:
    """Use the prepared project runtime when Cloud Run supplied one."""
    return os.environ.get("TESTGEN_PYTHON", sys.executable)


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
                command = [_test_python(), '-X', 'utf8', '-m', 'slipcover',  *(('--branch',) if branch_coverage else ()),
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


def measure_suite_coverage(*, tests_dir: Path, source_dir: T.Optional[Path], pytest_args='',
                           trace=None, isolate_tests=False, branch_coverage=True):
    """Runs an entire test suite and returns the coverage obtained."""

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as j:
        try:
            command = [_test_python(),
                     '-X', 'utf8',
                     '-m', 'slipcover',
                         *(('--source', source_dir) if source_dir else ()),
                         *(('--branch',) if branch_coverage else ()),
                         '--json', '--out', j.name,
                     '-m', 'pytest', *pytest_args.split(),
                         '--disable-warnings', '-x', tests_dir]

            if trace: trace(command)
            p = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if p.returncode not in (pytest.ExitCode.OK, pytest.ExitCode.NO_TESTS_COLLECTED):
                if trace: trace(f"tests rc={p.returncode}\n" + str(p.stdout, 'utf-8'))
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
