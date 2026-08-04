# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
from unittest.mock import patch
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Test when self.directory is set and Path(self.directory) in file_path.resolve().parents
    config = Config(skip=frozenset(), directory=str(tmp_path))
    assert config.is_skipped(file_path) is False

    # Test when self.directory is NOT in file_path.resolve().parents (else branch: file_name = str(file_path))
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    config_other = Config(skip=frozenset(), directory=str(other_dir))
    assert config_other.is_skipped(file_path) is False




def test_is_skipped_skips_list(tmp_path):
    file_path = tmp_path / "skipped_file.py"
    file_path.write_text("print(1)")

    # Test matching via skips list directly (absolute path match in for skip_path in self.skips)
    norm_path = str(file_path).replace("\\", "/")
    if norm_path[1:2] == ":":
        norm_path = norm_path[2:]
    config = Config(skip=frozenset([norm_path]))
    assert config.is_skipped(file_path) is True

    # Test matching via position[1] in self.skips (while loop over path parts)
    config_basename = Config(skip=frozenset(["skipped_file.py"]))
    assert config_basename.is_skipped(file_path) is True


def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "glob_test.py"
    file_path.write_text("print(1)")

    # Test matching via skip_globs (setting skip_glob instead of skip_globs)
    config = Config(skip_glob=frozenset(["*glob_test.py"]))
    assert config.is_skipped(file_path) is True


def test_is_skipped_nonexistent_file(tmp_path):
    nonexistent = tmp_path / "does_not_exist.py"

    # Test when file does not exist, is not a dir, and is not a link
    config = Config(skip=frozenset())
    assert config.is_skipped(nonexistent) is True


def test_is_skipped_skip_gitignore(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")

    # Test skip_gitignore branches
    # 1. folder in self.git_ls_files match via any(folder in path.parents for path in file_paths)
    config = Config(skip_gitignore=True)
    object.__setattr__(config, "git_ls_files", {tmp_path: [str(file_path.resolve())]})
    assert config.is_skipped(file_path) is False

    # 2. else branch calling _check_folder_git_ls_files and git_folder found but file not in git_ls_files
    config2 = Config(skip_gitignore=True)
    object.__setattr__(config2, "git_ls_files", {tmp_path: []})
    with patch.object(Config, "_check_folder_git_ls_files", return_value=tmp_path):
        assert config2.is_skipped(file_path) is True
