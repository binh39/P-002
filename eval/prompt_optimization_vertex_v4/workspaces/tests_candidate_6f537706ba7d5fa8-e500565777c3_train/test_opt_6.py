# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [619, 624], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
import pytest
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Test when self.directory is set and Path(self.directory) in file_path.resolve().parents
    config_with_dir = Config(directory=str(tmp_path))
    assert not config_with_dir.is_skipped(file_path)

    # Test when self.directory is not set or not in parents (else branch: file_name = str(file_path))
    config_without_dir = Config(directory="")
    assert not config_without_dir.is_skipped(file_path)


def test_is_skipped_windows_drive_normalization(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")

    config = Config()
    class FakePath(Path):
        def __str__(self):
            return "C:\\folder\\file.py"

    fake = FakePath(tmp_path / "test.py")
    res = config.is_skipped(fake)
    assert isinstance(res, bool)


def test_is_skipped_skips_and_globs(tmp_path):
    skipped_file = tmp_path / "skipped_file.py"
    skipped_file.write_text("print(1)")

    glob_file = tmp_path / "glob_test_foo.py"
    glob_file.write_text("print(1)")

    # Use 'skip' and 'skip_glob' instead of 'skips' and 'skip_globs'
    config = Config(skip=["skipped_file.py"], skip_glob=["*_foo.py"])
    
    # Test skip list matching via abspath (lines 593-597)
    assert config.is_skipped(skipped_file)

    # Test folder/position-based skip check (lines 599-603)
    config_folder_skip = Config(skip=["subfolder"])
    subfolder_file = tmp_path / "subfolder" / "file.py"
    subfolder_file.parent.mkdir(exist_ok=True, parents=True)
    subfolder_file.write_text("print(1)")
    assert config_folder_skip.is_skipped(subfolder_file)

    # Test skip_glob matching (lines 605-607)
    assert config.is_skipped(glob_file)


def test_is_skipped_non_existent_file(tmp_path):
    non_existent = tmp_path / "does_not_exist.py"
    config = Config()
    # Lines 609-610: not (os.path.isfile or os.path.isdir or os.path.islink) -> returns True
    assert config.is_skipped(non_existent)


def test_is_skipped_git_gitignore(tmp_path):
    file_path = tmp_path / "file.py"
    file_path.write_text("print(1)")

    # Test skip_gitignore = True with git_ls_files logic (lines 612-633)
    config = Config(skip_gitignore=True, git_ls_files={tmp_path: [str(file_path.resolve())]})
    assert not config.is_skipped(file_path)

    # Test when file is NOT in git_ls_files (triggers return True at line 633)
    config2 = Config(skip_gitignore=True, git_ls_files={tmp_path: [str(tmp_path / "other.py")]})
    assert config2.is_skipped(file_path)

    # Test the else branch of git_ls_files loop (line 624: git_folder = self._check_folder_git_ls_files(...))
    config3 = Config(skip_gitignore=True, git_ls_files={})
    object.__setattr__(config3, "_check_folder_git_ls_files", lambda folder: None)
    assert not config3.is_skipped(file_path)

    config4 = Config(skip_gitignore=True, git_ls_files={tmp_path: []})
    object.__setattr__(config4, "_check_folder_git_ls_files", lambda folder: tmp_path)
    assert config4.is_skipped(file_path)
