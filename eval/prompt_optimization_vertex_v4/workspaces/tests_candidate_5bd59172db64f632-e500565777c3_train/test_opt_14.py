# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [619, 624], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
import pytest
from isort.settings import Config


def test_is_skipped_directory_handling(tmp_path):
    # Test directory handling branches (lines 582-585)
    d = tmp_path / "sub"
    d.mkdir()
    f = d / "test.py"
    f.write_text("x = 1")

    # When self.directory is set and Path(self.directory) in file_path.resolve().parents
    config_with_dir = Config(directory=str(tmp_path))
    assert not config_with_dir.is_skipped(f)

    # When self.directory is not set (else branch)
    config_without_dir = Config(directory="")
    assert not config_without_dir.is_skipped(f)


def test_is_skipped_windows_drive_path():
    # Test Windows drive letter stripping (lines 590-591)
    config = Config()

    class DummyPath(Path):
        def __fspath__(self):
            return "C:/test.py"

    p = DummyPath("C:/test.py")
    
    # Non-existent file will return True at line 609, but normalized_path processing (lines 589-591) runs first.
    assert config.is_skipped(p) is True


def test_is_skipped_skips_and_globs(tmp_path):
    f = tmp_path / "skip_me.py"
    f.write_text("x = 1")

    # Test skips via list/parents (lines 593-603)
    config_skip = Config(skip=["skip_me.py"])
    assert config_skip.is_skipped(f)

    # Test skip_glob (lines 605-607)
    config_glob = Config(skip_glob=["*.py"])
    assert config_glob.is_skipped(f)


def test_is_skipped_nonexistent_file(tmp_path):
    # Test non-existent file check (lines 609-610)
    missing_file = tmp_path / "does_not_exist.py"
    config = Config()
    assert config.is_skipped(missing_file) is True


def test_is_skipped_skip_gitignore(tmp_path):
    # Test skip_gitignore branches (lines 612-633)
    f = tmp_path / "file.py"
    f.write_text("x = 1")

    # Create a config with skip_gitignore=True
    config = Config(skip_gitignore=True)

    # Case 1: file_path.name == ".git" (line 613-614)
    git_file = tmp_path / ".git"
    assert config.is_skipped(git_file) is True

    # Case 2: any(folder in path.parents for path in file_paths) matches (lines 619-622) via Config(git_ls_files=...)
    config_with_git_files = Config(
        skip_gitignore=True,
        git_ls_files={tmp_path: {str(f.resolve())}}
    )
    assert config_with_git_files.is_skipped(f) is False

    # Case 3: fallback to _check_folder_git_ls_files (line 624) returning None or folder without match
    config_empty_git = Config(
        skip_gitignore=True,
        git_ls_files={}
    )
    assert config_empty_git.is_skipped(f) is False

    # Case 4: git_folder is found, but file is not in git_ls_files and not a dir (lines 628-633)
    config_git_other = Config(
        skip_gitignore=True,
        git_ls_files={tmp_path: {str(tmp_path / "other.py")}}
    )
    assert config_git_other.is_skipped(f) is True
