# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}

import os
import stat
import sys
from unittest.mock import patch, MagicMock
import pytest
from isort.settings import Config, DEFAULT_CONFIG


def test_is_supported_filetype_extensions():
    config = DEFAULT_CONFIG
    # Supported extension
    assert config.is_supported_filetype("test.py") is True
    # Blocked extension
    assert config.is_supported_filetype("test.pex") is False


def test_is_supported_filetype_backup():
    config = DEFAULT_CONFIG
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo():
    config = DEFAULT_CONFIG
    # Mock os.stat to return a mode where stat.S_ISFIFO is True
    with patch("os.stat") as mock_stat, patch("stat.S_ISFIFO", return_value=True):
        mock_stat.return_value.st_mode = 0
        assert config.is_supported_filetype("some_fifo_file.ext") is False


def test_is_supported_filetype_os_error_on_open():
    config = DEFAULT_CONFIG
    # Non-existent file raises FileNotFoundError (which is an OSError)
    assert config.is_supported_filetype("non_existent_file_xyz_12345.ext") is False


def test_is_supported_filetype_shebang():
    config = DEFAULT_CONFIG
    
    # File with python shebang
    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.readline.return_value = b"#!/usr/bin/env python\n"
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch("os.stat") as mock_stat, patch("stat.S_ISFIFO", return_value=False):
            assert config.is_supported_filetype("script_with_shebang.ext") is True

    # File without python shebang
    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_file.readline.return_value = b"#!/bin/bash\n"
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch("os.stat") as mock_stat, patch("stat.S_ISFIFO", return_value=False):
            assert config.is_supported_filetype("script_without_shebang.ext") is False
