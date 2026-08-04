# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import sys
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config()
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=frozenset({"pex"}))
    assert config.is_supported_filetype("test.pex") is False


def test_is_supported_filetype_tilde_backup():
    config = Config()
    assert config.is_supported_filetype("test.txt~") is False


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="FIFOs/named pipes are not reliably supported across Windows in the same way as Unix."
)
def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    fifo_path = tmp_path / "test_fifo.txt"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, NotImplementedError, OSError):
        pytest.skip("os.mkfifo not available")

    assert config.is_supported_filetype(str(fifo_path)) is False


def test_is_supported_filetype_oserror_on_stat():
    config = Config()
    # Use a file path where open() will raise an OSError (e.g. trying to open a directory as a file on some OSes, 
    # or a path that causes an error). Or we can pass a path that triggers OSError in open().
    # On Windows, opening a directory with "rb" raises PermissionError/IsADirectoryError (which is an OSError).
    # To be safe and cross-platform without using tmp_path cleanup issues, we can use an invalid filename or a directory.
    # Actually, passing an empty string or a directory path usually causes OSError on open().
    # Let's pass a directory path if possible, or use a mocked path or invalid path.
    # Wait, os.stat on a directory succeeds, but open(dir, "rb") raises IsADirectoryError/PermissionError (OSError).
    # Let's test with a directory path directly!
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # stat succeeds on directory, S_ISFIFO is False, then open(tmpdir, "rb") raises OSError -> returns False
        assert config.is_supported_filetype(tmpdir) is False


def test_is_supported_filetype_shebang_match():
    import tempfile
    config = Config()
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "script_without_ext")
        with open(file_path, "wb") as f:
            f.write(b"#!/usr/bin/env python3\nprint('hello')\n")
        assert config.is_supported_filetype(file_path) is True


def test_is_supported_filetype_shebang_no_match():
    import tempfile
    config = Config()
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "script_without_ext_no_python")
        with open(file_path, "wb") as f:
            f.write(b"#!/bin/bash\necho 'hello'\n")
        assert config.is_supported_filetype(file_path) is False
