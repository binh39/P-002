# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}

import os
import stat
import pytest
from unittest.mock import patch, MagicMock
from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=["py"], blocked_extensions=[])
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(supported_extensions=[], blocked_extensions=["txt"])
    assert config.is_supported_filetype("test.txt") is False


def test_is_supported_filetype_tilde_backup():
    config = Config(supported_extensions=[], blocked_extensions=[])
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo():
    config = Config(supported_extensions=[], blocked_extensions=[])
    with patch("os.stat") as mock_stat, patch("stat.S_ISFIFO", return_value=True):
        assert config.is_supported_filetype("some_fifo_file") is False


def test_is_supported_filetype_os_error_on_stat():
    config = Config(supported_extensions=[], blocked_extensions=[])
    with patch("os.stat", side_effect=OSError):
        with patch("builtins.open", side_effect=OSError):
            assert config.is_supported_filetype("non_existent.py") is False


def test_is_supported_filetype_os_error_on_open():
    config = Config(supported_extensions=[], blocked_extensions=[])
    with patch("os.stat") as mock_stat, patch("stat.S_ISFIFO", return_value=False):
        with patch("builtins.open", side_effect=OSError):
            assert config.is_supported_filetype("restricted.py") is False


def test_is_supported_filetype_shebang_matching():
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    # Matching shebang
    mock_fp_match = MagicMock()
    mock_fp_match.readline.return_value = b"#!/usr/bin/env python\n"
    
    with patch("os.stat"), patch("stat.S_ISFIFO", return_value=False), patch("builtins.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_fp_match
        assert config.is_supported_filetype("script1") is True

    # Non-matching shebang
    mock_fp_nomatch = MagicMock()
    mock_fp_nomatch.readline.return_value = b"print('hello')\n"
    
    with patch("os.stat"), patch("stat.S_ISFIFO", return_value=False), patch("builtins.open") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_fp_nomatch
        assert config.is_supported_filetype("script2") is False
