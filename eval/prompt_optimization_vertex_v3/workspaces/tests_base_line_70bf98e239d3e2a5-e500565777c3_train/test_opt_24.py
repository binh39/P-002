# file: src\sample_repo\isort\isort\settings.py:518-541
# asked: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 532], [531, 536]]}
# gained: {"lines": [518, 519, 520, 521, 522, 523, 524, 527, 528, 530, 531, 533, 534, 536, 537, 538, 539, 540, 541], "branches": [[521, 522], [521, 523], [523, 524], [523, 527], [527, 528], [527, 530], [531, 536]]}

import os
import stat
import pytest
from isort.settings import Config


def test_is_supported_filetype(tmp_path):
    # 1. Test supported extension (Line 521-522)
    config = Config(supported_extensions=frozenset(["customext"]))
    supported_file = tmp_path / "test.customext"
    supported_file.write_text("print('hello')")
    assert config.is_supported_filetype(str(supported_file)) is True

    # 2. Test blocked extension (Line 523-524)
    config = Config(supported_extensions=frozenset(), blocked_extensions=frozenset(["blockedext"]))
    blocked_file = tmp_path / "test.blockedext"
    blocked_file.write_text("print('hello')")
    assert config.is_supported_filetype(str(blocked_file)) is False

    # 3. Test backup files ending with '~' (Line 527-528)
    config = Config()
    backup_file = tmp_path / "file.py~"
    backup_file.write_text("print('hello')")
    assert config.is_supported_filetype(str(backup_file)) is False

    # 4. Test FIFO special file (Line 531-532)
    fifo_file = tmp_path / "test_fifo.py"
    fifo_file.write_text("")
    try:
        os.mkfifo(str(fifo_file))
        assert config.is_supported_filetype(str(fifo_file)) is False
    except (AttributeError, OSError):
        pass

    # 5. Test OSError on os.stat / file checks (Line 533-534 / 539-540)
    # Using a file with an extension not in supported/blocked (e.g., .unknown)
    # so it reaches stat/open, and non-existent triggers OSError.
    non_existent = tmp_path / "does_not_exist.unknown"
    assert config.is_supported_filetype(str(non_existent)) is False

    # 6. Test file with valid shebang (Line 537-541 -> True)
    shebang_file = tmp_path / "shebang_script.unknown"
    shebang_file.write_bytes(b"#!/usr/bin/env python\nprint('hi')\n")
    assert config.is_supported_filetype(str(shebang_file)) is True

    # 7. Test file without shebang and not a python file (Line 537-541 -> False)
    plain_file = tmp_path / "plain_file.unknown"
    plain_file.write_bytes(b"Just some plain text without shebang.")
    assert config.is_supported_filetype(str(plain_file)) is False
