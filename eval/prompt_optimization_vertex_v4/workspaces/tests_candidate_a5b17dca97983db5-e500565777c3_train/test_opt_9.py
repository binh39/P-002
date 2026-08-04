# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files(tmp_path: Path):
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    (skipped_dir / "file.py").write_text("print(1)")

    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()
    script_py = normal_dir / "script.py"
    script_py.write_text("print(2)")
    txt_file = normal_dir / "not_supported.txt"
    txt_file.write_text("hello")

    direct_file = tmp_path / "direct_file.py"
    direct_file.write_text("print(3)")

    config = Config(skip=["skipped_dir"], ignore_whitespace=True)
    skipped: list[str] = []
    broken: list[str] = []

    paths = [str(tmp_path)]
    results = list(find(paths, config, skipped, broken))

    # Assertions
    assert str(script_py) in results
    assert str(direct_file) in results  # direct_file.py is a python file inside tmp_path, so it gets found
    assert str(skipped_dir / "file.py") not in results
    assert any("skipped_dir" in s for s in skipped)


def test_find_visited_dirs_symlink_or_duplicate(tmp_path: Path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    (sub_dir / "a.py").write_text("print(1)")

    sym_dir = tmp_path / "sym"
    try:
        os.symlink(sub_dir, sym_dir, target_is_directory=True)
    except OSError:
        return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    assert results.count(str(sub_dir / "a.py")) == 1


def test_find_skipped_file(tmp_path: Path):
    py_file = tmp_path / "skip_me.py"
    py_file.write_text("print(4)")

    config = Config(skip=["skip_me.py"])
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    assert len(skipped) > 0
    assert str(py_file) not in results


def test_find_broken_path(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.py"
    skipped: list[str] = []
    broken: list[str] = []
    config = Config()

    results = list(find([str(non_existent)], config, skipped, broken))
    assert str(non_existent) in broken
    assert results == []


def test_find_direct_file(tmp_path: Path):
    py_file = tmp_path / "direct.py"
    py_file.write_text("print(5)")

    skipped: list[str] = []
    broken: list[str] = []
    config = Config()

    results = list(find([str(py_file)], config, skipped, broken))
    assert results == [str(py_file)]
