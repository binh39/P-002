# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=["foo"])
    file_path = tmp_path / "test.foo"
    file_path.write_text("content")
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=["bar"])
    file_path = tmp_path / "test.bar"
    file_path.write_text("content")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_tilde_backup(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "test.py~"
    file_path.write_text("content")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "test_fifo"
    try:
        os.mkfifo(str(file_path))
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform/filesystem")
    
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_os_error_stat(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Pass a non-existent file or directory path that causes open/stat issues if needed,
    # or test when file doesn't exist during open/readline.
    non_existent = tmp_path / "does_not_exist.py"
    assert config.is_supported_filetype(str(non_existent)) is False


def test_is_supported_filetype_shebang(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    # File with shebang matching _SHEBANG_RE
    shebang_file = tmp_path / "script_with_shebang"
    shebang_file.write_bytes(b"#!/usr/bin/env python\nprint('hello')\n")
    assert config.is_supported_filetype(str(shebang_file)) is True

    # File without shebang
    no_shebang_file = tmp_path / "script_without_shebang"
    no_shebang_file.write_bytes(b"print('hello')\n")
    assert config.is_supported_filetype(str(no_shebang_file)) is False
