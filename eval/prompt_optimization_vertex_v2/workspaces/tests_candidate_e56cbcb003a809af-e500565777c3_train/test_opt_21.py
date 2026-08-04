# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import tempfile
import pytest
from pathlib import Path
from isort.settings import Config

def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=("customext",))
    assert config.is_supported_filetype("test.customext") is True

def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("blocked",))
    assert config.is_supported_filetype("test.blocked") is False

def test_is_supported_filetype_tilde_backup():
    config = Config()
    assert config.is_supported_filetype("file.py~") is False

def test_is_supported_filetype_fifo():
    config = Config()
    with tempfile.TemporaryDirectory() as tmpdir:
        fifo_path = os.path.join(tmpdir, "test_fifo")
        try:
            os.mkfifo(fifo_path)
        except (AttributeError, OSError):
            pytest.skip("os.mkfifo not supported on this platform")

        assert config.is_supported_filetype(fifo_path) is False

def test_is_supported_filetype_os_error_on_open():
    config = Config()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Passing a directory path will cause open(..., "rb") to raise an IsADirectoryError / OSError
        dir_path = os.path.join(tmpdir, "subdir")
        os.mkdir(dir_path)
        assert config.is_supported_filetype(dir_path) is False

def test_is_supported_filetype_shebang_matching():
    config = Config(supported_extensions=()) # ensure not matched by extension
    with tempfile.TemporaryDirectory() as tmpdir:
        # File with Python shebang
        py_shebang_file = os.path.join(tmpdir, "script_py")
        with open(py_shebang_file, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python\nprint('hello')")
        assert config.is_supported_filetype(py_shebang_file) is True

        # File without shebang
        no_shebang_file = os.path.join(tmpdir, "script_none")
        with open(no_shebang_file, "w", encoding="utf-8") as f:
            f.write("just some text\n")
        assert config.is_supported_filetype(no_shebang_file) is False
