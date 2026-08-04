# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config

def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=["py"], blocked_extensions=[])
    file_path = tmp_path / "test.py"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is True

def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=["txt"])
    file_path = tmp_path / "test.txt"
    file_path.write_text("some text")
    assert config.is_supported_filetype(str(file_path)) is False

def test_is_supported_filetype_tilde_backup(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "test.py~"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is False

def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "fifo_file"
    try:
        os.mkfifo(str(file_path))
    except (AttributeError, NotImplementedError, OSError):
        pytest.skip("os.mkfifo not supported on this platform")
    
    assert config.is_supported_filetype(str(file_path)) is False

def test_is_supported_filetype_os_stat_oserror(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Pass a non-existent file or something that causes stat to fail (if any, though non-existent will fail earlier at open or stat)
    # Actually, if file doesn't exist, stat raises OSError and is caught, then open raises OSError and returns False.
    non_existent = tmp_path / "non_existent.py"
    assert config.is_supported_filetype(str(non_existent)) is False

def test_is_supported_filetype_shebang(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "script_with_shebang"
    file_path.write_bytes(b"#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(file_path)) is True

def test_is_supported_filetype_no_shebang(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "script_without_shebang"
    file_path.write_bytes(b"print('hello')")
    assert config.is_supported_filetype(str(file_path)) is False
