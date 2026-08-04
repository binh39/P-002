# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config

def test_is_supported_filetype_supported_extension():
    config = Config()
    assert config.is_supported_filetype("test.py") is True

def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=frozenset(["txt"]))
    assert config.is_supported_filetype("test.txt") is False

def test_is_supported_filetype_tilde_backup():
    config = Config(
        supported_extensions=frozenset(["unknownext"]),
        blocked_extensions=frozenset()
    )
    assert config.is_supported_filetype("test.unknownext~") is False

def test_is_supported_filetype_fifo(tmp_path):
    config = Config(
        supported_extensions=frozenset(["unknownext"]),
        blocked_extensions=frozenset()
    )
    
    fifo_path = tmp_path / "test.unknownext"
    try:
        os.mkfifo(str(fifo_path))
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform/filesystem")

    assert config.is_supported_filetype(str(fifo_path)) is False

def test_is_supported_filetype_os_error_on_stat(tmp_path):
    config = Config(
        supported_extensions=frozenset(),
        blocked_extensions=frozenset()
    )

    non_existent = tmp_path / "does_not_exist.unknownext"
    assert config.is_supported_filetype(str(non_existent)) is False

def test_is_supported_filetype_shebang_match(tmp_path):
    config = Config(
        supported_extensions=frozenset(),
        blocked_extensions=frozenset()
    )

    file_path = tmp_path / "script.unknownext"
    file_path.write_text("#!/usr/bin/env python\nprint('hello')")
    
    assert config.is_supported_filetype(str(file_path)) is True

def test_is_supported_filetype_no_shebang_match(tmp_path):
    config = Config(
        supported_extensions=frozenset(),
        blocked_extensions=frozenset()
    )

    file_path = tmp_path / "script.unknownext"
    file_path.write_text("just some random text without shebang")
    
    assert config.is_supported_filetype(str(file_path)) is False
