# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import tempfile
from unittest.mock import patch
from pathlib import Path
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=("py",))
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("txt",))
    assert config.is_supported_filetype("test.txt") is False


def test_is_supported_filetype_backup_file():
    config = Config()
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fifo_path = os.path.join(tmp_dir, "fifo_file")
        try:
            os.mkfifo(fifo_path)
        except (AttributeError, OSError):
            pytest.skip("os.mkfifo not supported on this platform")

        config = Config()
        assert config.is_supported_filetype(fifo_path) is False




def test_is_supported_filetype_shebang_and_os_error_on_open():
    config = Config()

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Test file with python shebang
        py_file = os.path.join(tmp_dir, "script_with_shebang")
        with open(py_file, "w") as f:
            f.write("#!/usr/bin/env python\nprint('hello')")
        assert config.is_supported_filetype(py_file) is True

        # Test file without shebang
        no_shebang = os.path.join(tmp_dir, "script_without_shebang")
        with open(no_shebang, "w") as f:
            f.write("print('hello')")
        assert config.is_supported_filetype(no_shebang) is False

        # Test OSError when opening a directory instead of a file
        assert config.is_supported_filetype(tmp_dir) is False
