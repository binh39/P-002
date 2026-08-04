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
    config = Config(supported_extensions=("py",))
    assert config.is_supported_filetype("test.py") is True


def test_is_supported_filetype_blocked_extension():
    config = Config(blocked_extensions=("txt",))
    assert config.is_supported_filetype("test.txt") is False


def test_is_supported_filetype_tilde_backup():
    config = Config()
    assert config.is_supported_filetype("test.py~") is False


def test_is_supported_filetype_fifo_pipe():
    config = Config()
    with tempfile.TemporaryDirectory() as tmpdir:
        fifo_path = os.path.join(tmpdir, "my_fifo")
        try:
            os.mkfifo(fifo_path)
        except (AttributeError, NotImplementedError, OSError):
            pytest.skip("OS does not support mkfifo")
        
        assert config.is_supported_filetype(fifo_path) is False


def test_is_supported_filetype_oserror_on_stat():
    config = Config()
    # If the file does not exist, open() raises OSError (caught by lines 539-540), returning False.
    # We pass a non-extension-matching name to bypass `ext in self.supported_extensions` (since default includes .py).
    assert config.is_supported_filetype("nonexistent_file_123456789.unknownext") is False


def test_is_supported_filetype_shebang_match():
    config = Config()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".unknownext", delete=False) as tf:
        tf.write("#!/usr/bin/env python\nprint('hello')")
        tf_name = tf.name
    try:
        assert config.is_supported_filetype(tf_name) is True
    finally:
        os.remove(tf_name)


def test_is_supported_filetype_shebang_no_match():
    config = Config()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".unknownext", delete=False) as tf:
        tf.write("just some normal text without a shebang\n")
        tf_name = tf.name
    try:
        assert config.is_supported_filetype(tf_name) is False
    finally:
        os.remove(tf_name)
