# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from unittest.mock import patch
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=("py",))
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(blocked_extensions=("txt",))
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_tilde_backup(tmp_path):
    config = Config()
    file_path = tmp_path / "test.py~"
    file_path.write_text("print(1)")
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_fifo_pipe(tmp_path):
    config = Config()
    fifo_path = tmp_path / "my_fifo"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not available on this platform")

    assert config.is_supported_filetype(str(fifo_path)) is False


def test_is_supported_filetype_oserror_on_stat(tmp_path):
    config = Config()
    file_path = tmp_path / "test.xyz"
    file_path.write_text("print(1)")
    with patch("os.stat", side_effect=OSError):
        assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_oserror_on_open(tmp_path):
    config = Config()
    # Directory will cause open(..., "rb") to raise an IsADirectoryError (which is an OSError)
    dir_path = tmp_path / "subdir"
    dir_path.mkdir()
    assert config.is_supported_filetype(str(dir_path)) is False


def test_is_supported_filetype_shebang_match(tmp_path):
    config = Config()
    file_path = tmp_path / "script_without_ext"
    file_path.write_bytes(b"#!/usr/bin/env python\nprint(1)")
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_shebang_no_match(tmp_path):
    config = Config()
    file_path = tmp_path / "script_without_ext"
    file_path.write_bytes(b"some random text without shebang")
    assert config.is_supported_filetype(str(file_path)) is False
