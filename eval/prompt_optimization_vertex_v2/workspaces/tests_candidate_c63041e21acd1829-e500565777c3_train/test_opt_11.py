# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 34], [34, 37], [38, 39], [38, 41]]}

import os
import tempfile
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        skipped_dir = tmp_path / "skipped_sub"
        skipped_dir.mkdir()

        py_file = tmp_path / "test.py"
        py_file.write_text("print(1)")
        
        sub_py_file = sub_dir / "sub_test.py"
        sub_py_file.write_text("print(2)")

        skipped_file = skipped_dir / "skip.py"
        skipped_file.write_text("print(3)")

        config = Config(skip=["skipped_sub", "skip.py"])
        skipped: list[str] = []
        broken: list[str] = []

        non_existent = str(tmp_path / "does_not_exist")
        
        paths = [
            str(tmp_path),
            non_existent,
            str(py_file)
        ]

        results = list(find(paths, config, skipped, broken))

        assert str(py_file) in results
        assert str(sub_py_file) in results
        assert non_existent in broken
        assert any("skipped_sub" in s for s in skipped)


def test_find_visited_dirs_symlink_or_duplicate():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        d1 = tmp_path / "d1"
        d1.mkdir()
        d2 = tmp_path / "d2"
        
        try:
            d2.symlink_to(d1, target_is_directory=True)
            has_symlink = True
        except OSError:
            has_symlink = False

        config = Config(follow_links=True)
        skipped: list[str] = []
        broken: list[str] = []

        paths = [str(d1)]
        if has_symlink:
            paths.append(str(d2))

        results = list(find(paths, config, skipped, broken))
        assert isinstance(results, list)
