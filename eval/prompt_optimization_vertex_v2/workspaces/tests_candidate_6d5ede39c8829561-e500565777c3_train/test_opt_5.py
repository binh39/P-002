# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
import tempfile

from isort.files import find
from isort.settings import Config


def test_find_directory_and_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure:
        # tmpdir/
        #   skipped_dir/
        #   supported.py
        #   unsupported.txt
        #   skipped_file.py
        sub_dir = Path(tmpdir) / "skipped_dir"
        sub_dir.mkdir()

        supported_file = Path(tmpdir) / "supported.py"
        supported_file.write_text("print(1)")

        unsupported_file = Path(tmpdir) / "unsupported.txt"
        unsupported_file.write_text("text")

        skipped_file = Path(tmpdir) / "skipped_file.py"
        skipped_file.write_text("print(2)")

        config = Config(
            skip=["skipped_dir", "skipped_file.py"],
            skip_glob=[],
        )

        skipped = []
        broken = []
        
        results = list(find([tmpdir], config, skipped, broken))

        assert str(supported_file) in results
        assert str(unsupported_file) not in results
        assert str(sub_dir) in skipped
        assert str(skipped_file.resolve()) in [os.path.abspath(s) for s in skipped]
        assert broken == []


def test_find_broken_path():
    config = Config()
    skipped = []
    broken = []
    non_existent = "/non/existent/path/123456"

    results = list(find([non_existent], config, skipped, broken))
    assert results == []
    assert non_existent in broken


def test_find_direct_file_path():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tf:
        tf_name = tf.name
    try:
        config = Config()
        skipped = []
        broken = []

        results = list(find([tf_name], config, skipped, broken))
        assert results == [tf_name]
        assert skipped == []
        assert broken == []
    finally:
        os.unlink(tf_name)


def test_find_visited_dirs_symlink():
    # Tests the `resolved_path in visited_dirs` branch (e.g. via symlink pointing back)
    if os.name == "nt":
        # Symlinks on Windows often require admin privileges; skip if not supported or risky
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        real_subdir = Path(tmpdir) / "real"
        real_subdir.mkdir()
        
        py_file = real_subdir / "foo.py"
        py_file.write_text("pass")

        link_dir = Path(tmpdir) / "link"
        try:
            link_dir.symlink_to(real_subdir, target_is_directory=True)
        except OSError:
            # If symlinks aren't permitted, skip the test
            return

        config = Config(follow_links=True)
        skipped = []
        broken = []

        results = list(find([tmpdir], config, skipped, broken))
        assert str(py_file) in results
