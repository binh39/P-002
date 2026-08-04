# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 523, 527, 530, 531, 536, 537, 538, 539, 540, 541], "branches": [[521, 523], [523, 527], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config

def test_is_supported_filetype_fifo(tmp_path):
    config = Config()
    # Create a FIFO file if supported by the OS (skip or handle OSError if not supported on Windows, etc.)
    fifo_path = tmp_path / "test_fifo"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, NotImplementedError, OSError):
        pytest.skip("os.mkfifo not supported on this platform")

    # This should trigger stat.S_ISFIFO branch returning False
    assert config.is_supported_filetype(str(fifo_path)) is False

def test_is_supported_filetype_os_error_on_open():
    config = Config()
    # A path that causes open(..., 'rb') to raise an OSError (e.g. pointing to a directory)
    # Note: os.path.splitext on a directory name doesn't have an extension unless specified,
    # and it won't match supported/blocked extensions.
    # Opening a directory in 'rb' mode raises IsADirectoryError (which is an OSError).
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pass the directory path itself
        assert config.is_supported_filetype(tmpdir) is False

def test_is_supported_filetype_shebang_matching(tmp_path):
    config = Config()
    
    # File with a python shebang and unknown extension
    f_python = tmp_path / "script.unknown_ext"
    f_python.write_bytes(b"#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(f_python)) is True

    # File with a non-matching first line and unknown extension
    f_other = tmp_path / "other.unknown_ext"
    f_other.write_bytes(b"not a shebang line\n")
    assert config.is_supported_filetype(str(f_other)) is False
