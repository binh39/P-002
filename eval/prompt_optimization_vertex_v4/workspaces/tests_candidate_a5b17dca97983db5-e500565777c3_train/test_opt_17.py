# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config

def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=["py"], blocked_extensions=[])
    # Extension in supported_extensions (line 521 -> 522)
    assert config.is_supported_filetype("test.py") is True

def test_is_supported_filetype_blocked_extension():
    config = Config(supported_extensions=[], blocked_extensions=["txt"])
    # Extension in blocked_extensions (line 523 -> 524)
    assert config.is_supported_filetype("test.txt") is False

def test_is_supported_filetype_editor_backup():
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Ends with '~' (line 527 -> 528)
    assert config.is_supported_filetype("test.py~") is False

def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    fifo_path = tmp_path / "fifo_file"
    try:
        os.mkfifo(str(fifo_path))
    except (AttributeError, NotImplementedError):
        pytest.skip("os.mkfifo not supported on this platform")
    
    # FIFO file check (lines 530-532)
    assert config.is_supported_filetype(str(fifo_path)) is False

def test_is_supported_filetype_oserror_on_stat():
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Non-existent file raises OSError on stat/open, catching in except OSError: pass and then except OSError: return False
    assert config.is_supported_filetype("non_existent_file_123456.py") is False

def test_is_supported_filetype_shebang(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    # File with shebang (lines 536-541)
    shebang_file = tmp_path / "script_with_shebang"
    shebang_file.write_bytes(b"#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(shebang_file)) is True

    # File without shebang
    no_shebang_file = tmp_path / "script_without_shebang"
    no_shebang_file.write_bytes(b"print('hello')")
    assert config.is_supported_filetype(str(no_shebang_file)) is False
