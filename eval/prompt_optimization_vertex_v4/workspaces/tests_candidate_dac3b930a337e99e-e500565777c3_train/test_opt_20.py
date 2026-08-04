# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
from unittest.mock import patch
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Config with directory set to sub_dir (file_path is inside sub_dir)
    config = Config(directory=str(sub_dir), skip=("skipped.py",))
    assert config.is_skipped(file_path) is False

    # Config with directory set to a parent of tmp_path (file_path resolve parents includes directory)
    config2 = Config(directory=str(tmp_path), skip=("skipped.py",))
    assert config2.is_skipped(file_path) is False






def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "test_ignore.py"
    file_path.write_text("print(1)")

    config = Config(skip_glob=("*ignore*",))
    assert config.is_skipped(file_path) is True


def test_is_skipped_non_existent_file(tmp_path):
    file_path = tmp_path / "non_existent.py"
    config = Config()
    # Neither file, dir, nor link exists
    assert config.is_skipped(file_path) is True


def test_is_skipped_git_ignore_paths(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")

    git_folder = tmp_path / "git_root"
    git_folder.mkdir()

    # Case 1: any(folder in path.parents for path in file_paths) matches
    config = Config(
        skip_gitignore=True,
        git_ls_files={git_folder: {str(file_path.resolve())}},
    )
    with patch.object(Path, "parents", [git_folder]):
        assert config.is_skipped(file_path) is False

    # Case 2: folder not in path.parents, falls back to _check_folder_git_ls_files
    config2 = Config(
        skip_gitignore=True,
        git_ls_files={git_folder: set()},
    )
    with patch.object(config2, "_check_folder_git_ls_files", return_value=git_folder):
        # file_path is not a dir and resolved path not in git_ls_files[git_folder] -> skipped
        assert config2.is_skipped(file_path) is True

        # resolved path IS in git_ls_files[git_folder] -> not skipped
        config3 = Config(
            skip_gitignore=True,
            git_ls_files={git_folder: {str(file_path.resolve())}},
        )
        with patch.object(config3, "_check_folder_git_ls_files", return_value=git_folder):
            assert config3.is_skipped(file_path) is False
