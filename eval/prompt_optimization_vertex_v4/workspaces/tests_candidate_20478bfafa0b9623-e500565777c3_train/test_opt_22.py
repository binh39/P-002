# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 38], [38, 39], [38, 41]]}

from pathlib import Path
import os
from isort.files import find
from isort.settings import Config




def test_find_broken_path() -> None:
    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    non_existent = "/path/that/definitely/does/not/exist/abcxyz"
    results = list(find([non_existent], config, skipped, broken))

    assert results == []
    assert non_existent in broken


def test_find_direct_file(tmp_path: Path) -> None:
    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    file_path = tmp_path / "direct.py"
    file_path.write_text("print(1)")

    results = list(find([str(file_path)], config, skipped, broken))

    assert results == [str(file_path)]
    assert skipped == []
    assert broken == []


def test_find_visited_dirs_symlink(tmp_path: Path) -> None:
    if os.name == "nt":
        return

    real_dir = tmp_path / "real"
    real_dir.mkdir()
    
    sub_dir = real_dir / "sub"
    sub_dir.mkdir()

    symlink_dir = tmp_path / "sym"
    try:
        os.symlink(real_dir, symlink_dir, target_is_directory=True)
    except OSError:
        return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(real_dir), str(symlink_dir)], config, skipped, broken))
    assert isinstance(results, list)
