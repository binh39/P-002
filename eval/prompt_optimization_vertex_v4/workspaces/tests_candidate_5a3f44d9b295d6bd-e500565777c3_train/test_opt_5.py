# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_file_directly(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("print(1)")

    skipped = []
    broken = []
    config = Config()

    result = list(find([str(py_file)], config, skipped, broken))
    assert result == [str(py_file)]
    assert skipped == []
    assert broken == []


def test_find_broken_path():
    skipped = []
    broken = []
    config = Config()

    non_existent = "/non/existent/path/that/definitely/does/not/exist.py"
    result = list(find([non_existent], config, skipped, broken))
    assert result == []
    assert broken == [non_existent]
    assert skipped == []


def test_find_directory_with_skipped_and_supported_files(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    
    py_file = sub_dir / "module.py"
    py_file.write_text("x = 1")
    
    skipped_file = sub_dir / "skip_me.py"
    skipped_file.write_text("y = 2")

    skipped_dir = tmp_path / "skip_dir"
    skipped_dir.mkdir()
    skipped_dir_file = skipped_dir / "ignored.py"
    skipped_dir_file.write_text("z = 3")

    config = Config(
        skip=["skip_me.py", "skip_dir"],
        skip_glob=[],
    )

    skipped = []
    broken = []

    result = list(find([str(tmp_path)], config, skipped, broken))

    # module.py should be yielded, skip_me.py and skip_dir (and its contents) should be skipped
    assert str(py_file) in result
    assert str(skipped_file) in skipped
    # Depending on how isort config checks directories, skip_dir or its full path will be in skipped
    assert any("skip_dir" in s for s in skipped)


def test_find_symlink_visited_dirs(tmp_path):
    # Test directory symlink / already visited dir handling (resolved_path in visited_dirs)
    if not hasattr(Path, "symlink_to"):
        return  # Symlinks not supported on this platform/filesystem

    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "a.py").write_text("print(1)")

    sym_dir = tmp_path / "sym"
    try:
        sym_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        # Symlinks might fail without admin privileges on Windows
        return

    config = Config(follow_links=True)
    skipped = []
    broken = []

    result = list(find([str(tmp_path)], config, skipped, broken))
    # Should find a.py through real, but sym should hit visited_dirs and prune
    assert len([r for r in result if r.endswith("a.py")]) == 1
