# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [619, 624], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
import pytest
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "file.py"
    file_path.write_text("x = 1")

    # When self.directory is set and Path(self.directory) is in file_path.resolve().parents
    config = Config(directory=str(tmp_path))
    assert not config.is_skipped(file_path)

    # When self.directory is NOT in parents (falls back to str(file_path))
    config_no_dir = Config(directory="")
    assert not config_no_dir.is_skipped(file_path)




def test_is_skipped_parent_folder_in_skips(tmp_path):
    sub_dir = tmp_path / "ignored_folder"
    sub_dir.mkdir()
    file_path = sub_dir / "file.py"
    file_path.write_text("x = 1")

    # Test while position[1] in self.skips loop (parent components matched)
    config = Config(skip=frozenset(["ignored_folder"]))
    assert config.is_skipped(file_path)


def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "glob_match.py"
    file_path.write_text("x = 1")

    config = Config(skip_glob=frozenset(["*_match.py"]))
    assert config.is_skipped(file_path)


def test_is_skipped_non_existent_file(tmp_path):
    non_existent = tmp_path / "ghost.py"

    config = Config()
    assert config.is_skipped(non_existent)


def test_is_skipped_skip_gitignore_logic(tmp_path, monkeypatch):
    file_path = tmp_path / "tracked.py"
    file_path.write_text("x = 1")

    # Create config with git_ls_files pre-populated via constructor override or subclassing/recreating
    # Since _Config is frozen, we can instantiate Config with git_ls_files passed via config overrides if supported,
    # or instantiate using Config(git_ls_files=...)
    
    # 1. Force git_ls_files to contain a folder that is in file_path.parents and file_path not in git_ls_files[git_folder]
    config_skipped = Config(skip_gitignore=True, git_ls_files={tmp_path: set()})
    assert config_skipped.is_skipped(file_path)

    # 2. Force git_ls_files to contain a folder that is in file_path.parents and file_path IS in git_ls_files[git_folder]
    config_not_skipped = Config(skip_gitignore=True, git_ls_files={tmp_path: {str(file_path.resolve())}})
    assert not config_not_skipped.is_skipped(file_path)

    # 3. When folder is not in any file_path.parents, it invokes _check_folder_git_ls_files (returns None)
    config_check = Config(skip_gitignore=True, git_ls_files={})
    monkeypatch.setattr(config_check, "_check_folder_git_ls_files", lambda folder: None)
    assert not config_check.is_skipped(file_path)
