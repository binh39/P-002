# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import tempfile
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension():
    config = Config()
    # Ensure a supported extension like .py returns True immediately
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("pyc",))
    # A blocked extension should return False
    assert config.is_supported_filetype("test.pyc") is False


def test_is_supported_filetype_tilde_backup():
    config = Config()
    # Editor backup files ending with ~ should return False
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo_stat_oserror():
    # Pass a path that doesn't exist to trigger OSError in os.stat (lines 533-534)
    # and then raise OSError in open (lines 539-540)
    config = Config()
    non_existent = "non_existent_file_abc123.txt"
    assert config.is_supported_filetype(non_existent) is False


def test_is_supported_filetype_with_shebang():
    config = Config()
    fd, path = tempfile.mkstemp(text=False)
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"#!/usr/bin/env python\nprint('hello')\n")
        assert config.is_supported_filetype(path) is True
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def test_is_supported_filetype_without_shebang():
    config = Config()
    fd, path = tempfile.mkstemp(text=False)
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"just some text\n")
        assert config.is_supported_filetype(path) is False
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
