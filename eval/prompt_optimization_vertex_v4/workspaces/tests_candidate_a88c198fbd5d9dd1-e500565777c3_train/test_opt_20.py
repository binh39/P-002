# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 31], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_walk_and_files(tmp_path: Path):
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    (skipped_dir / "sub.py").write_text("print(1)")

    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()
    test_py = normal_dir / "test.py"
    test_py.write_text("print(2)")
    ignored_txt = normal_dir / "ignored.txt"
    ignored_txt.write_text("text")
    skipped_file = normal_dir / "skipped_file.py"
    skipped_file.write_text("print(3)")

    symlink_dir = tmp_path / "symlink_dir"
    try:
        symlink_dir.symlink_to(normal_dir, target_is_directory=True)
    except OSError:
        symlink_dir = None

    # Use skip_glob or config.skip appropriately so is_skipped matches the path correctly
    config = Config(
        skip=[str(skipped_dir / "sub.py"), str(skipped_file)],
        skip_glob=[str(skipped_dir / "*")],
        follow_links=True,
    )

    skipped: list[str] = []
    broken: list[str] = []

    paths = [str(normal_dir), str(skipped_dir)]
    if symlink_dir:
        paths.append(str(symlink_dir))

    results = list(find(paths, config, skipped, broken))

    assert str(test_py) in results
    assert str(skipped_dir / "sub.py") not in results
    assert str(ignored_txt) not in results


def test_find_broken_and_direct_file(tmp_path: Path):
    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    non_existent = tmp_path / "does_not_exist.py"
    direct_file = tmp_path / "direct.py"
    direct_file.write_text("print(4)")

    results = list(find([str(non_existent), str(direct_file)], config, skipped, broken))

    assert str(non_existent) in broken
    assert str(direct_file) in results
