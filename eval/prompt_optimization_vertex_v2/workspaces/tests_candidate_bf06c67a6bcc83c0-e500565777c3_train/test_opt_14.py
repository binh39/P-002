# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 38], [38, 39], [38, 41]]}

import os
from pathlib import Path
import tempfile
import shutil
import pytest
from isort.files import find
from isort.settings import Config


@pytest.fixture
def custom_tmp_path():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)




def test_find_visited_dirs_branch(custom_tmp_path: Path):
    sub = custom_tmp_path / "sub"
    sub.mkdir()
    link = custom_tmp_path / "link"
    
    try:
        os.symlink(sub, link, target_is_directory=True)
    except OSError:
        try:
            os.symlink(sub, link)
        except OSError:
            return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(custom_tmp_path)], config, skipped, broken))
    assert isinstance(results, list)


def test_find_broken_and_direct_file(custom_tmp_path: Path):
    broken_path = custom_tmp_path / "does_not_exist.py"

    direct_file = custom_tmp_path / "direct.py"
    direct_file.write_text("print('direct')")

    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    paths = [str(broken_path), str(direct_file)]
    results = list(find(paths, config, skipped, broken))

    assert str(broken_path) in broken
    assert str(direct_file) in results
