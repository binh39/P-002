# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 536, 537, 538, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}

import os
import stat
import unittest.mock as mock
from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=("py",))
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("txt",))
    assert config.is_supported_filetype("test.txt") is False


def test_is_supported_filetype_backup_file():
    config = Config()
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo():
    config = Config()
    class MockStat:
        st_mode = stat.S_IFIFO

    with mock.patch("os.stat", return_value=MockStat()):
        assert config.is_supported_filetype("some_fifo_file") is False




def test_is_supported_filetype_with_shebang():
    config = Config()
    class MockStat:
        st_mode = 0

    mock_file = mock.mock_open(read_data=b"#!/usr/bin/env python\n")
    with mock.patch("os.stat", return_value=MockStat()), \
         mock.patch("builtins.open", mock_file):
        assert config.is_supported_filetype("script_with_shebang") is True


def test_is_supported_filetype_without_shebang():
    config = Config()
    class MockStat:
        st_mode = 0

    mock_file = mock.mock_open(read_data=b"print('hello')\n")
    with mock.patch("os.stat", return_value=MockStat()), \
         mock.patch("builtins.open", mock_file):
        assert config.is_supported_filetype("script_without_shebang") is False
