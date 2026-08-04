# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 536, 537, 539, 540], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}

import os
import stat
from unittest.mock import patch, MagicMock
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=("py",))
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("txt",))
    assert config.is_supported_filetype("test.txt") is False


def test_is_supported_filetype_tilde_backup():
    config = Config()
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo():
    config = Config(supported_extensions=("unknown",))
    
    mock_mode = stat.S_IFIFO | 0o644
    with patch("isort.settings.os.stat") as mock_stat, \
         patch("isort.settings.stat.S_ISFIFO", return_value=True):
        mock_stat.return_value.st_mode = mock_mode
        assert config.is_supported_filetype("fifo_file") is False








def test_is_supported_filetype_open_os_error():
    config = Config(supported_extensions=("unknown",))
    with patch("isort.settings.os.stat"), \
         patch("isort.settings.stat.S_ISFIFO", return_value=False), \
         patch("isort.settings.open", side_effect=OSError):
        assert config.is_supported_filetype("unreadable_file") is False
