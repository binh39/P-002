# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=["customext"])
    file_path = tmp_path / "test.customext"
    file_path.write_text("some content")
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(blocked_extensions=["blockedext"])
    file_path = tmp_path / "test.blockedext"
    file_path.write_text("some content")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_backup_file(tmp_path):
    config = Config()
    file_path = tmp_path / "test.py~"
    file_path.write_text("some content")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    file_path = tmp_path / "test_fifo"
    try:
        os.mkfifo(str(file_path))
    except (AttributeError, NotImplementedError, OSError):
        pytest.skip("OS does not support mkfifo")
    
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_os_error_on_open(tmp_path):
    config = Config()
    # Passing a directory path will cause open(..., 'rb') to raise an IsADirectoryError (which is an OSError)
    dir_path = tmp_path / "subdir"
    dir_path.mkdir()
    assert config.is_supported_filetype(str(dir_path)) is False


def test_is_supported_filetype_shebang(tmp_path):
    config = Config()
    file_path = tmp_path / "script_with_shebang"
    file_path.write_bytes(b"#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(file_path)) is True

    file_path_no_shebang = tmp_path / "script_without_shebang"
    file_path_no_shebang.write_bytes(b"print('hello')")
    assert config.is_supported_filetype(str(file_path_no_shebang)) is False
