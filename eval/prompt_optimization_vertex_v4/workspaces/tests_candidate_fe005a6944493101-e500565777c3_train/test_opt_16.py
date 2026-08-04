# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=["foo"])
    f = tmp_path / "test.foo"
    f.write_text("content")
    assert config.is_supported_filetype(str(f)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(blocked_extensions=["bar"], supported_extensions=[])
    f = tmp_path / "test.bar"
    f.write_text("content")
    assert config.is_supported_filetype(str(f)) is False


def test_is_supported_filetype_tilde_backup(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    f = tmp_path / "test.py~"
    f.write_text("content")
    assert config.is_supported_filetype(str(f)) is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    fifo_path = tmp_path / "test_fifo.py"
    try:
        os.mkfifo(str(fifo_path))
    except (AttributeError, NotImplementedError):
        pytest.skip("os.mkfifo not supported on this platform/filesystem")
    
    assert config.is_supported_filetype(str(fifo_path)) is False


def test_is_supported_filetype_os_error_on_open(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Pass a directory path, which will raise an OSError (or IsADirectoryError / PermissionError) when opened in "rb" mode on some platforms,
    # or alternatively a non-existent file or special path.
    # Actually, opening a directory with "rb" raises IsADirectoryError (an OSError) on Linux/macOS.
    dir_path = tmp_path / "some_dir.py"
    dir_path.mkdir()
    assert config.is_supported_filetype(str(dir_path)) is False


def test_is_supported_filetype_shebang_match(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    f = tmp_path / "script_with_shebang"
    f.write_bytes(b"#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(f)) is True


def test_is_supported_filetype_shebang_no_match(tmp_path):
    config = Config(supported_extensions=[], blocked_extensions=[])
    f = tmp_path / "script_without_shebang"
    f.write_bytes(b"print('hello')")
    assert config.is_supported_filetype(str(f)) is False
