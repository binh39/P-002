# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8], "branches": []}

import os
import tempfile
from pathlib import Path
from isort.files import find
from isort.settings import Config




def test_find_symlink_visited_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        sub_file = target_dir / "sub.py"
        sub_file.write_text("x = 1")

        symlink_dir = tmp_path / "symlink"
        try:
            os.symlink(target_dir, symlink_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            return

        config = Config(follow_links=True)
        skipped: list[str] = []
        broken: list[str] = []

        try:
            results = list(find([str(tmp_path)], config, skipped, broken))
            assert str(sub_file) in results
        finally:
            if symlink_dir.is_symlink() or symlink_dir.exists():
                try:
                    symlink_dir.rmdir()
                except OSError:
                    pass
