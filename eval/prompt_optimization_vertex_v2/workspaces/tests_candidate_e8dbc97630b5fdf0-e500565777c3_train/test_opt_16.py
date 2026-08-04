# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}

import os
import stat
import tempfile
import pytest
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

def test_is_supported_filetype_fifo(monkeypatch):
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    # Mock stat and S_ISFIFO to simulate a FIFO file
    class DummyStat:
        st_mode = 0
        
    monkeypatch.setattr(os, "stat", lambda p: DummyStat())
    monkeypatch.setattr(stat, "S_ISFIFO", lambda mode: True)
    
    with tempfile.NamedTemporaryFile() as tmp:
        assert config.is_supported_filetype(tmp.name) is False

def test_is_supported_filetype_os_error_on_open():
    config = Config(supported_extensions=[], blocked_extensions=[])
    # Passing a non-existent file path will cause open() to raise OSError
    assert config.is_supported_filetype("non_existent_file_path_123456.xyz") is False

def test_is_supported_filetype_shebang():
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"#!/usr/bin/env python\nprint('hello')")
        tmp_name = tmp.name
        
    try:
        assert config.is_supported_filetype(tmp_name) is True
    finally:
        os.remove(tmp_name)

def test_is_supported_filetype_no_shebang():
    config = Config(supported_extensions=[], blocked_extensions=[])
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"just some normal text without shebang")
        tmp_name = tmp.name
        
    try:
        assert config.is_supported_filetype(tmp_name) is False
    finally:
        os.remove(tmp_name)
