# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
from pathlib import Path
import pytest

from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=("foo",))
    assert config.is_supported_filetype("test.foo") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("bar",))
    assert config.is_supported_filetype("test.bar") is False


def test_is_supported_filetype_tilde_backup():
    config = Config()
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    fifo_path = tmp_path / "test_fifo.py"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform")

    assert config.is_supported_filetype(str(fifo_path)) is False


def test_is_supported_filetype_os_error_on_open(monkeypatch):
    config = Config(supported_extensions=())

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    assert config.is_supported_filetype("some_file.py") is False


def test_is_supported_filetype_shebang_and_no_shebang(tmp_path):
    config = Config(supported_extensions=())
    
    # File with Python shebang
    shebang_file = tmp_path / "script_with_shebang"
    shebang_file.write_bytes(b"#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(shebang_file)) is True

    # File without shebang
    no_shebang_file = tmp_path / "script_without_shebang"
    no_shebang_file.write_bytes(b"print('hello')")
    assert config.is_supported_filetype(str(no_shebang_file)) is False
