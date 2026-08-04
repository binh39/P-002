# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import os
import tempfile
import pytest

from isort.files import find
from isort.settings import Config


def test_find_directory_and_file_cases():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        
        skipped_dir = tmp_path / "skipped_dir"
        skipped_dir.mkdir()
        
        valid_dir = tmp_path / "valid_dir"
        valid_dir.mkdir()
        
        py_file = valid_dir / "test.py"
        py_file.write_text("print(1)\n")
        
        skipped_file = valid_dir / "skip.py"
        skipped_file.write_text("print(2)\n")
        
        txt_file = valid_dir / "readme.txt"
        txt_file.write_text("hello\n")

        config = Config(
            skip=["skipped_dir", "skip.py"],
            directory=str(tmp_path),
        )

        skipped: list[str] = []
        broken: list[str] = []

        non_existent = str(tmp_path / "does_not_exist.py")
        
        paths = [
            str(tmp_path),
            non_existent,
            str(py_file),
        ]

        results = list(find(paths, config, skipped, broken))

        assert non_existent in broken
        assert str(py_file) in results
        assert len(skipped) > 0


def test_find_visited_dirs_and_symlinks():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        py_file = sub_dir / "foo.py"
        py_file.write_text("x = 1\n")

        link_dir = tmp_path / "link"
        try:
            link_dir.symlink_to(sub_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            pass

        config = Config(follow_links=True, directory=str(tmp_path))
        skipped: list[str] = []
        broken: list[str] = []

        results = list(find([str(tmp_path)], config, skipped, broken))
        assert str(py_file) in results
