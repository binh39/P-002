# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=["foo"])
    file_path = tmp_path / "test.foo"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(blocked_extensions=["bar"], supported_extensions=[])
    file_path = tmp_path / "test.bar"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_backup_file(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "test.py~"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    file_path = tmp_path / "test_fifo"
    try:
        os.mkfifo(str(file_path))
    except (AttributeError, NotImplementedError, OSError):
        pytest.skip("os.mkfifo not supported on this platform")

    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_os_error_on_open(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Pass a directory or non-existent file or something that causes OSError on open(..., "rb")
    # Actually, opening a directory with "rb" on Windows/Linux raises PermissionError/IsADirectoryError (which are OSErrors).
    dir_path = tmp_path / "some_dir"
    dir_path.mkdir()
    assert config.is_supported_filetype(str(dir_path)) is False


def test_is_supported_filetype_shebang(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    file_with_shebang = tmp_path / "script_with_shebang"
    file_with_shebang.write_bytes(b"#!/usr/bin/env python\nprint('hi')")
    assert config.is_supported_filetype(str(file_with_shebang)) is True

    file_without_shebang = tmp_path / "script_without_shebang"
    file_without_shebang.write_bytes(b"print('hi')")
    assert config.is_supported_filetype(str(file_without_shebang)) is False
