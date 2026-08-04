# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 38, 41], "branches": [[14, 0], [14, 15], [15, 38], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config




def test_find_file_skip(tmp_path: Path):
    py_file = tmp_path / "skip_me.py"
    py_file.write_text("print('skip')")

    config = Config(skip=[str(py_file)])
    skipped = []
    broken = []

    results = list(find([str(py_file)], config, skipped, broken))

    assert str(py_file) in results
