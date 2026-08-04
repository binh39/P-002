# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import tempfile
import shutil
from isort.files import find
from isort.settings import Config


def test_find_file_path() -> None:
    temp_dir = tempfile.mkdtemp()
    try:
        py_file = Path(temp_dir) / "test.py"
        py_file.write_text("print(1)")

        config = Config()
        skipped: list[str] = []
        broken: list[str] = []

        results = list(find([str(py_file)], config, skipped, broken))
        assert results == [str(py_file)]
        assert skipped == []
        assert broken == []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_find_broken_path() -> None:
    temp_dir = tempfile.mkdtemp()
    try:
        non_existent = Path(temp_dir) / "does_not_exist.py"

        config = Config()
        skipped: list[str] = []
        broken: list[str] = []

        results = list(find([str(non_existent)], config, skipped, broken))
        assert results == []
        assert skipped == []
        assert broken == [str(non_existent)]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_find_directory_walk_and_skip() -> None:
    temp_dir = tempfile.mkdtemp()
    try:
        tmp_path = Path(temp_dir)
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()
        
        skipped_dir = tmp_path / "skip_dir"
        skipped_dir.mkdir()

        supported_file = sub_dir / "code.py"
        supported_file.write_text("x = 1")

        skipped_file = sub_dir / "skip_me.py"
        skipped_file.write_text("x = 2")

        unsupported_file = sub_dir / "text.txt"
        unsupported_file.write_text("hello")

        config = Config(
            skip=["skip_dir", "skip_me.py"],
        )
        skipped: list[str] = []
        broken: list[str] = []

        results = list(find([str(tmp_path)], config, skipped, broken))

        assert str(supported_file) in results
        assert str(unsupported_file) not in results  # not a supported filetype
        assert str(skipped_file) not in results
        assert str(skipped_file.resolve()) in [Path(s).resolve() for s in skipped] or any("skip_me.py" in s for s in skipped)
        assert str(skipped_dir.resolve()) in [Path(s).resolve() for s in skipped] or any("skip_dir" in s for s in skipped)
        assert broken == []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
