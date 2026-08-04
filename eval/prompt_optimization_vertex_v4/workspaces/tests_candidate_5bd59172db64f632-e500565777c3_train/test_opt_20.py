# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype_supported_extension(tmp_path):
    config = Config()
    # supported_extensions typically includes 'py', 'pyi', etc.
    d = tmp_path / "test.py"
    d.write_text("print('hello')")
    assert config.is_supported_filetype(str(d)) is True


def test_is_supported_filetype_blocked_extension(tmp_path):
    config = Config(blocked_extensions=("txt",))
    d = tmp_path / "test.txt"
    d.write_text("hello")
    assert config.is_supported_filetype(str(d)) is False


def test_is_supported_filetype_backup_file(tmp_path):
    config = Config()
    # Ends with ~
    d = tmp_path / "test.py~"
    d.write_text("print('hello')")
    assert config.is_supported_filetype(str(d)) is False


def test_is_supported_filetype_fifo(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    fifo_path = tmp_path / "test_fifo.unknownext"
    try:
        os.mkfifo(fifo_path)
    except (AttributeError, OSError):
        pytest.skip("os.mkfifo not supported on this platform")

    assert config.is_supported_filetype(str(fifo_path)) is False


def test_is_supported_filetype_os_error_on_stat(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    # Pass a path that causes stat to fail (e.g. non-existent file or inaccessible path)
    non_existent = str(tmp_path / "does_not_exist.unknownext")
    assert config.is_supported_filetype(non_existent) is False


def test_is_supported_filetype_shebang_match(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    d = tmp_path / "script_with_shebang.unknownext"
    d.write_text("#!/usr/bin/env python\nprint('hi')")
    assert config.is_supported_filetype(str(d)) is True


def test_is_supported_filetype_shebang_no_match(tmp_path):
    config = Config(supported_extensions=(), blocked_extensions=())
    d = tmp_path / "script_without_shebang.unknownext"
    d.write_text("just some text\nwithout shebang")
    assert config.is_supported_filetype(str(d)) is False
