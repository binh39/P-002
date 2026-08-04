# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import tempfile
import pytest
from pathlib import Path
from isort.settings import Config

def test_is_supported_filetype_supported_extension():
    config = Config(supported_extensions=("customext",))
    assert config.is_supported_filetype("test.customext") is True

def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("blockedext",))
    assert config.is_supported_filetype("test.blockedext") is False

def test_is_supported_filetype_tilde_backup():
    config = Config()
    assert config.is_supported_filetype("somefile.py~") is False

def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    fifo_path = tmp_path / "my_fifo"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform/filesystem")
    
    assert config.is_supported_filetype(str(fifo_path)) is False

def test_is_supported_filetype_os_error_on_stat():
    config = Config()
    # A non-existent file will raise an OSError in stat()
    assert config.is_supported_filetype("non_existent_file_abc123.xyz") is False

def test_is_supported_filetype_shebang_and_read_errors(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())

    # File with shebang
    shebang_file = tmp_path / "script.unknown"
    shebang_file.write_text("#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(shebang_file)) is True

    # File without shebang
    no_shebang = tmp_path / "noshebang.unknown"
    no_shebang.write_text("just some random text")
    assert config.is_supported_filetype(str(no_shebang)) is False

    # Directory instead of file (opening a directory in "rb" raises an OSError on many OSes, or returns empty/fails read)
    # Testing OSError during open/readline by passing a path that cannot be opened as a file for reading
    # Alternatively, we can use a path that raises OSError (like a directory on Linux/macOS when opened with 'rb')
    dir_path = tmp_path / "somedir.unknown"
    dir_path.mkdir()
    assert config.is_supported_filetype(str(dir_path)) is False
