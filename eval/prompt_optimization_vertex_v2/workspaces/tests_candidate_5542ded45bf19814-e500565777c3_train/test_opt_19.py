# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}

import os
import stat
import tempfile
import pytest
from unittest.mock import patch
from isort.settings import Config

def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=["py"], blocked_extensions=[])
    assert config.is_supported_filetype("test.py") is True

def test_is_supported_filetype_blocked_extension():
    config = Config(supported_extensions=[], blocked_extensions=["txt"])
    assert config.is_supported_filetype("test.txt") is False

def test_is_supported_filetype_tilde_backup():
    config = Config(supported_extensions=[], blocked_extensions=[])
    assert config.is_supported_filetype("some_file~") is False

def test_is_supported_filetype_fifo():
    config = Config(supported_extensions=[], blocked_extensions=[])
    with patch("stat.S_ISFIFO", return_value=True):
        with patch("os.stat"):
            with patch("builtins.open", create=True):
                assert config.is_supported_filetype("some_fifo") is False

def test_is_supported_filetype_os_error_stat():
    config = Config(supported_extensions=[], blocked_extensions=[])
    with patch("os.stat", side_effect=OSError):
        with patch("builtins.open", side_effect=OSError):
            assert config.is_supported_filetype("non_existent_file.unknown") is False

def test_is_supported_filetype_shebang():
    config = Config(supported_extensions=[], blocked_extensions=[])
    with tempfile.TemporaryDirectory() as tmpdir:
        # File with shebang
        f_shebang = os.path.join(tmpdir, "script_with_shebang")
        with open(f_shebang, "wb") as f:
            f.write(b"#!/usr/bin/env python\nprint('hello')")
        assert config.is_supported_filetype(f_shebang) is True

        # File without shebang
        f_no_shebang = os.path.join(tmpdir, "script_without_shebang")
        with open(f_no_shebang, "wb") as f:
            f.write(b"print('hello')")
        assert config.is_supported_filetype(f_no_shebang) is False
