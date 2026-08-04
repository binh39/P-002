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

    # 1. directory is set and file_path is inside directory
    config = Config(directory=str(sub_dir), skip=["ignored.py"])
    assert not config.is_skipped(file_path)

    # 2. directory is not set or file_path is not in directory parents
    config2 = Config(directory="", skip=["ignored.py"])
    assert not config2.is_skipped(file_path)




def test_is_skipped_parent_dir_in_skips(tmp_path):
    skip_dir = tmp_path / "skip_me"
    skip_dir.mkdir()
    file_path = skip_dir / "nested" / "file.py"
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_text("print(1)")

    config = Config(skip=["skip_me"])
    assert config.is_skipped(file_path) is True


def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "test_ignore.py"
    file_path.write_text("print(1)")

    config = Config(skip_glob=["*_ignore.py"])
    assert config.is_skipped(file_path) is True


def test_is_skipped_non_existent_file(tmp_path):
    missing_file = tmp_path / "non_existent.py"
    config = Config()
    assert config.is_skipped(missing_file) is True


def test_is_skipped_git_ignore_branches(tmp_path, monkeypatch):
    git_dir = tmp_path / "repo"
    git_dir.mkdir()
    file_path = git_dir / "file.py"
    file_path.write_text("print(1)")

    # Test skip_gitignore = True
    config = Config(skip_gitignore=True, directory=str(git_dir))

    # Populate object's mutable dictionary _git_ls_files or mutate git_ls_files directly if attribute/property allows,
    # or mock object dict / method _check_folder_git_ls_files.
    # Config uses `git_ls_files` which is a field on the dataclass/class.
    # Let's bypass frozen check by modifying object dict directly or mocking `_check_folder_git_ls_files`.
    object.__setattr__(config, "git_ls_files", {git_dir: {str(file_path.resolve())}})
    assert config.is_skipped(file_path) is False

    # Case B: not in git_ls_files via `for folder in ... else:` fallback to _check_folder_git_ls_files
    object.__setattr__(config, "git_ls_files", {})
    monkeypatch.setattr(config, "_check_folder_git_ls_files", lambda folder: None)
    assert config.is_skipped(file_path) is False

    # Case C: git_folder returned by _check_folder_git_ls_files, but file not in git_ls_files for that folder -> skipped (returns True)
    monkeypatch.setattr(config, "_check_folder_git_ls_files", lambda folder: git_dir)
    object.__setattr__(config, "git_ls_files", {git_dir: {str(tmp_path / "other.py")}})
    assert config.is_skipped(file_path) is True
