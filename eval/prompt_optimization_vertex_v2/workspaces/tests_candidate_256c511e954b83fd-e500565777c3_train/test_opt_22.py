# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 536, 537, 538, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import tempfile
import pytest
from pathlib import Path
from isort.settings import Config

@pytest.fixture
def temp_dir():
    d = tempfile.TemporaryDirectory()
    yield Path(d.name)
    d.cleanup()

def test_is_supported_filetype_supported_extension(temp_dir):
    config = Config(supported_extensions=("customext",))
    file_path = temp_dir / "test.customext"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is True

def test_is_supported_filetype_blocked_extension(temp_dir):
    config = Config(blocked_extensions=("blockedext",))
    file_path = temp_dir / "test.blockedext"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is False

def test_is_supported_filetype_tilde_backup(temp_dir):
    config = Config()
    file_path = temp_dir / "test.py~"
    file_path.write_text("print('hello')")
    assert config.is_supported_filetype(str(file_path)) is False

def test_is_supported_filetype_fifo_pipe(temp_dir):
    config = Config()
    fifo_path = temp_dir / "test_pipe.py"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform/filesystem")
    
    assert config.is_supported_filetype(str(fifo_path)) is False



def test_is_supported_filetype_shebang_matching(temp_dir):
    config = Config()
    
    shebang_file = temp_dir / "script_with_shebang"
    shebang_file.write_text("#!/usr/bin/env python\nprint('hello')")
    assert config.is_supported_filetype(str(shebang_file)) is True

    no_shebang_file = temp_dir / "script_without_shebang"
    no_shebang_file.write_text("print('hello')")
    assert config.is_supported_filetype(str(no_shebang_file)) is False
