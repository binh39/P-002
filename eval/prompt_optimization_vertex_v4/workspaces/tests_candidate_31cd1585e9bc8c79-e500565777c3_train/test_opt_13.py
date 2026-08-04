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

        # Create subdirectories and files
        skipped_dir = tmp_path / "skipped_dir"
        skipped_dir.mkdir()
        
        normal_dir = tmp_path / "normal_dir"
        normal_dir.mkdir()

        py_file = normal_dir / "test.py"
        py_file.write_text("print(1)")

        txt_file = normal_dir / "test.txt"
        txt_file.write_text("hello")

        skipped_file = normal_dir / "skipped.py"
        skipped_file.write_text("print(2)")

        # Config with skipped dir and skipped file and supported filetypes
        config = Config(
            skip=["skipped_dir", "skipped.py"],
            directory=str(tmp_path),
            supported_extensions=tuple(["py"]),
        )

        skipped: list[str] = []
        broken: list[str] = []

        # Test passing a directory path
        results = list(find([str(tmp_path)], config, skipped, broken))

        assert str(py_file) in results
        assert str(txt_file) not in results  # not a supported filetype
        assert str(skipped_dir) in skipped
        assert os.path.abspath(skipped_file) in skipped

        # Test passing a direct file path (not a directory, exists)
        single_file_results = list(find([str(py_file)], config, skipped, broken))
        assert single_file_results == [str(py_file)]

        # Test passing a broken (non-existent) path
        broken_path = str(tmp_path / "does_not_exist.py")
        broken_results = list(find([broken_path], config, skipped, broken))
        assert broken_results == []
        assert broken_path in broken


def test_find_visited_dirs_symlink_or_duplicate(tmp_path):
    tmp_path = tmp_path.resolve()
    sub = tmp_path / "sub"
    sub.mkdir()
    
    link = tmp_path / "link"
    try:
        link.symlink_to(sub, target_is_directory=True)
    except OSError:
        # Symlinks might not be supported on some platforms (e.g. Windows without admin)
        return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    # Should complete without infinite recursion and hit resolved_path in visited_dirs
    assert isinstance(results, list)
