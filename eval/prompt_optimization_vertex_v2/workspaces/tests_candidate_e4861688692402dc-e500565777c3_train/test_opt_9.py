# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import tempfile
import os

from isort.settings import Config
from isort.files import find


def test_find_directory_walk_and_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        
        skipped_dir = tmp_path / "skipped_dir"
        skipped_dir.mkdir()

        # Create a python file inside sub_dir
        py_file = sub_dir / "test.py"
        py_file.write_text("print(1)")

        # Create a non-supported file to test is_supported_filetype branch
        txt_file = sub_dir / "test.txt"
        txt_file.write_text("hello")

        # Create a skipped file inside sub_dir
        skipped_py_file = sub_dir / "skip_me.py"
        skipped_py_file.write_text("print(2)")

        symlink_dir = tmp_path / "symlink_dir"
        try:
            os.symlink(sub_dir, symlink_dir, target_is_directory=True)
        except OSError:
            pass

        config = Config(
            skip=["skip_me.py", "skipped_dir"],
            follow_links=True,
        )

        skipped = []
        broken = []

        results = list(find([str(tmp_path)], config, skipped, broken))

        assert str(py_file) in results
        assert str(txt_file) not in results
        assert str(skipped_py_file) in skipped or str(skipped_py_file.absolute()) in skipped
        assert str(skipped_dir) in skipped or str(skipped_dir.absolute()) in skipped


def test_find_broken_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        broken_path = Path(tmpdir) / "does_not_exist.py"
        skipped = []
        broken = []
        config = Config()

        results = list(find([str(broken_path)], config, skipped, broken))

        assert broken_path.name in broken[0] or str(broken_path) in broken
        assert results == []


def test_find_direct_file_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "direct.py"
        py_file.write_text("x = 1")

        skipped = []
        broken = []
        config = Config()

        results = list(find([str(py_file)], config, skipped, broken))

        assert results == [str(py_file)]
        assert skipped == []
        assert broken == []
