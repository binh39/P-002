# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files(tmp_path: Path) -> None:
    # Setup directory structure:
    # tmp_path/
    #   ├── normal.py (supported)
    #   ├── skipped.py (skipped by config via filename/basename)
    #   ├── ignored.txt (unsupported filetype)
    #   └── sub/
    #         └── sub.py (supported)

    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()

    normal_py = tmp_path / "normal.py"
    normal_py.write_text("print(1)")

    skipped_py = tmp_path / "skipped.py"
    skipped_py.write_text("print(2)")

    ignored_txt = tmp_path / "ignored.txt"
    ignored_txt.write_text("text")

    sub_py = sub_dir / "sub.py"
    sub_py.write_text("print(3)")

    # Configure isort to skip by filename pattern/basename so is_skipped matches correctly
    config = Config(skip=["skipped.py"])

    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))

    # Assertions
    assert str(normal_py) in results
    assert str(sub_py) in results
    assert str(skipped_py) not in results
    assert any("skipped.py" in s for s in skipped)
    assert not broken


def test_find_broken_and_direct_file(tmp_path: Path) -> None:
    direct_py = tmp_path / "direct.py"
    direct_py.write_text("print(4)")

    non_existent = str(tmp_path / "does_not_exist.py")

    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    paths = [str(direct_py), non_existent]
    results = list(find(paths, config, skipped, broken))

    assert results == [str(direct_py)]
    assert broken == [non_existent]
    assert skipped == []
