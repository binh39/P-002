# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
import tempfile
import shutil
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files():
    temp_dir = tempfile.mkdtemp()
    try:
        d = Path(temp_dir) / "subdir"
        d.mkdir()
        
        skipped_dir = d / "skipped_dir"
        skipped_dir.mkdir()
        
        sub_sub_dir = d / "sub_sub"
        sub_sub_dir.mkdir()

        # Supported file type
        py_file = d / "test.py"
        py_file.write_text("print(1)")

        # Skipped file type / path
        skipped_file = d / "skipped.py"
        skipped_file.write_text("print(2)")

        # Unsupported file type
        txt_file = d / "test.txt"
        txt_file.write_text("hello")

        config = Config(
            skip=["skipped.py", "skipped_dir"],
        )

        skipped = []
        broken = []
        
        results = list(find([str(d)], config, skipped, broken))

        assert str(py_file) in results
        assert str(txt_file) not in results
        assert str(skipped_file) in skipped
        assert str(skipped_dir) in skipped
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_find_visited_dirs_symlink():
    temp_dir = tempfile.mkdtemp()
    try:
        real_dir = Path(temp_dir) / "real"
        real_dir.mkdir()
        
        # Create a symlink pointing to real_dir inside another dir
        link_dir = Path(temp_dir) / "link"
        try:
            os.symlink(real_dir, link_dir, target_is_directory=True)
        except OSError:
            # Symlinks might not be supported on some platforms (e.g. Windows without admin)
            return

        config = Config(follow_links=True)
        skipped = []
        broken = []

        results = list(find([str(temp_dir)], config, skipped, broken))
        assert isinstance(results, list)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_find_broken_and_direct_file():
    temp_dir = tempfile.mkdtemp()
    try:
        broken_path = str(Path(temp_dir) / "non_existent.py")

        direct_file = Path(temp_dir) / "direct.py"
        direct_file.write_text("print('direct')")

        config = Config()
        skipped = []
        broken = []

        results = list(find([broken_path, str(direct_file)], config, skipped, broken))

        assert broken_path in broken
        assert str(direct_file) in results
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
