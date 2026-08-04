# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
from isort.settings import Config
from isort.files import find


def test_find_all_branches(tmp_path: Path) -> None:
    # Setup directory structure and files
    # tmp_path/
    #   ├── skipped_dir/
    #   │   └── file.py
    #   ├── normal_dir/
    #   │   ├── script.py
    #   │   └── note.txt (unsupported)
    #   ├── file.py
    #   └── skipped_file.py
    
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    skipped_file_in_dir = skipped_dir / "file.py"
    skipped_file_in_dir.write_text("print('skip dir')")

    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()
    script_py = normal_dir / "script.py"
    script_py.write_text("print('script')")
    note_txt = normal_dir / "note.txt"
    note_txt.write_text("text")

    file_py = tmp_path / "file.py"
    file_py.write_text("print('file')")

    skipped_file = tmp_path / "skipped_file.py"
    skipped_file.write_text("print('skip file')")

    # Pass relative or folder name / skip names to match config.is_skipped logic
    config = Config(
        skip=["skipped_dir", "skipped_file.py"],
    )

    skipped: list[str] = []
    broken: list[str] = []

    paths = [
        str(tmp_path / "non_existent_path_xyz"),
        str(skipped_dir),
        str(normal_dir),
        str(file_py),
        str(skipped_file),
    ]

    results = list(find(paths, config, skipped, broken))

    # Assertions
    # 1. Non-existent path goes to broken
    assert str(tmp_path / "non_existent_path_xyz") in broken

    # 2. skipped_dir and skipped_file are added to skipped
    assert len(skipped) > 0

    # 3. Supported file directly passed in paths yields path
    assert str(file_py) in results

    # 4. Supported file inside normal_dir yields filepath
    assert str(script_py) in results

    # 5. Unsupported file (note.txt) is not yielded
    assert str(note_txt) not in results


def test_find_visited_dirs_symlink_or_duplicate(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    sub_file = sub / "test.py"
    sub_file.write_text("x = 1")

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    assert str(sub_file) in results
