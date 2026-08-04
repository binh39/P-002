# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 31], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import os
import tempfile
from isort.files import find
from isort.settings import Config


def test_find_directory_traversal_and_file_filtering():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        normal_dir = tmp_path / "normal_dir"
        normal_dir.mkdir()
        script_py = normal_dir / "script.py"
        script_py.write_text("print('hello')", encoding="utf-8")
        ignored_txt = normal_dir / "ignored.txt"
        ignored_txt.write_text("some text", encoding="utf-8")

        skipped_dir = tmp_path / "skipped_dir"
        skipped_dir.mkdir()
        other_py = skipped_dir / "other.py"
        other_py.write_text("print('world')", encoding="utf-8")

        direct_file = tmp_path / "direct_file.py"
        direct_file.write_text("print('direct')", encoding="utf-8")

        config = Config(
            skip=["skipped_dir"],
            skip_glob=[],
        )

        skipped: list[str] = []
        broken: list[str] = []

        paths = [str(normal_dir), str(skipped_dir), str(direct_file)]
        results = list(find(paths, config, skipped, broken))

        assert str(script_py) in results
        assert str(direct_file) in results
        assert str(other_py) not in results
        assert any("skipped_dir" in s for s in skipped)
        assert broken == []


def test_find_broken_path():
    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    paths = ["non_existent_path_123456.py"]
    results = list(find(paths, config, skipped, broken))

    assert results == []
    assert broken == ["non_existent_path_123456.py"]
    assert skipped == []


def test_find_visited_dirs_symlink():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()
        py_file = real_dir / "test.py"
        py_file.write_text("x = 1", encoding="utf-8")

        link_dir = tmp_path / "link_dir"
        try:
            link_dir.symlink_to(real_dir, target_is_directory=True)
        except OSError:
            # If symlinks aren't supported on the OS/filesystem, skip symlink test logic gracefully
            return

        config = Config(follow_links=True)
        skipped: list[str] = []
        broken: list[str] = []

        paths = [str(real_dir), str(link_dir)]
        results = list(find(paths, config, skipped, broken))

        assert str(py_file) in results
