# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config

def test_is_supported_filetype_supported_extension():
    config = Config()
    # default supported extensions usually includes py
    assert config.is_supported_filetype("test.py") is True

def test_is_supported_filetype_blocked_extension():
    # Config is a frozen dataclass, so override via constructor kwargs instead of direct assignment
    config = Config(blocked_extensions=frozenset(["txt"]))
    assert config.is_supported_filetype("test.txt") is False

def test_is_supported_filetype_backup_file():
    config = Config()
    # File ending with ~ but extension not in supported/blocked
    assert config.is_supported_filetype("test.unknown~") is False

def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    fifo_path = tmp_path / "test_fifo.unknown"
    try:
        os.mkfifo(str(fifo_path))
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not available or permitted on this system")

    assert config.is_supported_filetype(str(fifo_path)) is False

def test_is_supported_filetype_os_error_on_open(tmp_path):
    config = Config()
    # A directory will raise IsADirectoryError / OSError when opened with "rb"
    dir_path = tmp_path / "sub"
    dir_path.mkdir()
    assert config.is_supported_filetype(str(dir_path)) is False

def test_is_supported_filetype_shebang_match(tmp_path):
    config = Config()
    file_path = tmp_path / "script.unknown"
    file_path.write_bytes(b"#!/usr/bin/env python\nprint('hello')\n")
    assert config.is_supported_filetype(str(file_path)) is True

def test_is_supported_filetype_no_shebang_match(tmp_path):
    config = Config()
    file_path = tmp_path / "data.unknown"
    file_path.write_bytes(b"just some random text without shebang\n")
    assert config.is_supported_filetype(str(file_path)) is False
