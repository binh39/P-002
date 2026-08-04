# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config(supported_extensions=("py",))
    file_path = tmp_path / "test.py"
    file_path.write_text("print('hello')")
    
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(blocked_extensions=("txt",))
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello")
    
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_tilde_backup(tmp_path):
    config = Config()
    file_path = tmp_path / "test.py~"
    file_path.write_text("print('hello')")
    
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    file_path = tmp_path / "fifo_file"
    
    # Create a FIFO file if supported by the OS (Unix-like)
    try:
        os.mkfifo(str(file_path))
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform")
        
    assert config.is_supported_filetype(str(file_path)) is False


def test_is_supported_filetype_os_error_on_stat(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    
    # A non-existent file with extension in supported_extensions (or default supported extensions like py)
    # matches supported_extensions before it tries to stat or open!
    # By passing a non-existent file with an unsupported extension (e.g. .xyz),
    # it won't match supported or blocked, won't end with ~, stat/open will raise OSError, returning False.
    non_existent = str(tmp_path / "non_existent_file_12345.xyz")
    assert config.is_supported_filetype(non_existent) is False


def test_is_supported_filetype_shebang(tmp_path):
    config = Config()
    
    file_path = tmp_path / "script_no_ext"
    file_path.write_bytes(b"#!/usr/bin/env python\nprint('hi')")
    
    assert config.is_supported_filetype(str(file_path)) is True


def test_is_supported_filetype_no_shebang(tmp_path):
    config = Config()
    
    file_path = tmp_path / "plain_no_ext"
    file_path.write_bytes(b"just some plain text without shebang")
    
    assert config.is_supported_filetype(str(file_path)) is False
