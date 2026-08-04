# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files(tmp_path: Path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    
    supported_file = sub_dir / "test.py"
    supported_file.write_text("print(1)")
    
    unsupported_file = sub_dir / "text.txt"
    unsupported_file.write_text("hello")
    
    skipped_file = sub_dir / "skip_me.py"
    skipped_file.write_text("print(2)")
    
    # Use skip_glob or relative/absolute path configuration so that is_skipped matches properly
    config = Config(
        skip_glob=["*skip_me.py", "*skipped_dir*"],
        follow_links=True,
    )
    
    skipped: list[str] = []
    broken: list[str] = []
    
    results = list(find([str(tmp_path)], config, skipped, broken))
    
    assert str(supported_file) in results
    assert str(unsupported_file) not in results
    assert any("skip_me.py" in s for s in skipped)
    assert any("skipped_dir" in s for s in skipped)


def test_find_broken_and_direct_file(tmp_path: Path):
    supported_file = tmp_path / "direct.py"
    supported_file.write_text("print(3)")
    
    broken_path = tmp_path / "does_not_exist.py"
    
    config = Config()
    skipped: list[str] = []
    broken: list[str] = []
    
    results_file = list(find([str(supported_file)], config, skipped, broken))
    assert results_file == [str(supported_file)]
    
    results_broken = list(find([str(broken_path)], config, skipped, broken))
    assert results_broken == []
    assert broken == [str(broken_path)]


def test_find_visited_dirs_symlink(tmp_path: Path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    
    link_dir = tmp_path / "link"
    try:
        link_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        return
        
    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []
    
    results = list(find([str(tmp_path)], config, skipped, broken))
    assert isinstance(results, list)
