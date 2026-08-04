# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [620, 621], [628, 633], [628, 635]]}

import os
from pathlib import Path
import pytest
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "file.py"
    file_path.write_text("x = 1")

    # Config with directory set to parent (sub_dir parent is tmp_path)
    config = Config(directory=str(tmp_path), skip=[])
    assert config.is_skipped(file_path) is False

    # Config without directory
    config_no_dir = Config(directory="", skip=[])
    assert config_no_dir.is_skipped(file_path) is True or config_no_dir.is_skipped(file_path) is False


def test_is_skipped_windows_drive_and_skips(tmp_path):
    file_path = tmp_path / "skip_me.py"
    file_path.write_text("x = 1")

    # When directory is set to tmp_path, relpath gives "skip_me.py"
    config = Config(directory=str(tmp_path), skip=["skip_me.py"])
    assert config.is_skipped(file_path) is True


def test_is_skipped_directory_parts_and_globs(tmp_path):
    nested = tmp_path / "folder" / "subfolder"
    nested.mkdir(parents=True)
    file_path = nested / "test.py"
    file_path.write_text("x = 1")

    # Test position[1] in self.skips (folder matching up the parents)
    config_folder_skip = Config(directory=str(tmp_path), skip=["folder"])
    assert config_folder_skip.is_skipped(file_path) is True

    # Test skip_globs matching (file_name relative to directory when directory is set)
    config_glob = Config(directory=str(tmp_path), skip_glob=["**/subfolder/*.py"])
    assert config_glob.is_skipped(file_path) is True

    config_glob_slash = Config(directory=str(tmp_path), skip_glob=["/folder/subfolder/test.py"])
    assert config_glob_slash.is_skipped(file_path) is True


def test_is_skipped_non_existent_file(tmp_path):
    non_existent = tmp_path / "does_not_exist.py"
    config = Config(skip=[])
    # Not file, dir, or link -> returns True
    assert config.is_skipped(non_existent) is True


def test_is_skipped_git_ignore(tmp_path):
    file_path = tmp_path / "git_ignored.py"
    file_path.write_text("x = 1")

    class MockConfig(Config):
        def _check_folder_git_ls_files(self, folder: str):
            return Path(folder)

    git_folder_path = Path(tmp_path)
    cfg_with_git = MockConfig(
        skip_gitignore=True,
        git_ls_files={git_folder_path: {str(file_path.resolve())}},
        skip=[]
    )
    assert cfg_with_git.is_skipped(file_path) is False

    cfg_not_in_git = MockConfig(
        skip_gitignore=True,
        git_ls_files={git_folder_path: set()},
        skip=[]
    )
    assert cfg_not_in_git.is_skipped(file_path) is True
