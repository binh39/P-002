# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import tempfile
import os

from isort.files import find
from isort.settings import Config


def test_find_directories_and_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create subdirectories and files
        skipped_dir = tmp_path / "skipped_dir"
        skipped_dir.mkdir()
        
        normal_dir = tmp_path / "normal_dir"
        normal_dir.mkdir()
        
        py_file = normal_dir / "test.py"
        py_file.write_text("print(1)")
        
        skipped_file = normal_dir / "skipped.py"
        skipped_file.write_text("print(2)")
        
        non_py_file = normal_dir / "test.txt"
        non_py_file.write_text("hello")

        # Config with skip_glob or skip matching the filenames/dirs to ensure is_skipped triggers
        config = Config(
            skip=["skipped_dir", "skipped.py"],
        )

        skipped = []
        broken = []

        paths = [
            str(tmp_path),
            str(tmp_path / "non_existent_path_12345"),
            str(py_file),
        ]

        results = list(find(paths, config, skipped, broken))

        assert str(py_file) in results
        assert str(tmp_path / "non_existent_path_12345") in broken
        assert str(py_file) in results  # direct path yields path (line 41)
        assert len(skipped) > 0
        assert any("skipped_dir" in s for s in skipped) or any("skipped.py" in s for s in skipped)
