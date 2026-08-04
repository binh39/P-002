# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config

def test_is_supported_filetype_supported_extension():
    # Pass supported_extensions via constructor overrides to avoid FrozenInstanceError
    config = Config(supported_extensions=("py",))
    assert config.is_supported_filetype("test.py") is True

def test_is_supported_filetype_blocked_extension():
    config = Config(supported_extensions=(), blocked_extensions=("txt",))
    assert config.is_supported_filetype("test.txt") is False

def test_is_supported_filetype_backup_file():
    config = Config(supported_extensions=(), blocked_extensions=())
    assert config.is_supported_filetype("test.py~") is False

def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    fifo_path = tmp_path / "test_fifo"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        pytest.skip("OS does not support mkfifo")
    
    try:
        assert config.is_supported_filetype(str(fifo_path)) is False
    finally:
        if fifo_path.exists():
            fifo_path.unlink()

def test_is_supported_filetype_os_error_stat(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    non_existent = tmp_path / "does_not_exist.py"
    # stat() raises OSError, code should handle via except OSError: pass
    # and then try to open it, which will raise OSError and return False
    assert config.is_supported_filetype(str(non_existent)) is False

def test_is_supported_filetype_shebang_match(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    f = tmp_path / "script"
    f.write_text("#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(f)) is True

def test_is_supported_filetype_shebang_no_match(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    f = tmp_path / "script"
    f.write_text("just some random text without shebang")
    assert config.is_supported_filetype(str(f)) is False
