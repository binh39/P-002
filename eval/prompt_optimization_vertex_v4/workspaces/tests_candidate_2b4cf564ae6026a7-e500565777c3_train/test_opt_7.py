# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
from unittest.mock import patch
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    config = Config(directory=str(sub_dir))
    assert config.is_skipped(file_path) is False

    config_no_dir = Config(directory="")
    assert config_no_dir.is_skipped(file_path) is False


def test_is_skipped_windows_path_drive(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")
    config = Config()

    with patch("isort.settings.str") as mock_str:
        mock_str.side_effect = lambda obj: "C:\\path\\to\\file.py" if isinstance(obj, Path) else str(obj)
        with patch("os.path.isfile", return_value=True):
            assert config.is_skipped(file_path) is False


def test_is_skipped_skips_and_globs(tmp_path):
    file_path = tmp_path / "skip_me.py"
    file_path.write_text("print(1)")

    # Test skips via list match and directory position match
    config = Config(skip=["skip_me.py"])
    assert config.is_skipped(file_path) is True

    sub_path = tmp_path / "folder" / "sub" / "file.py"
    sub_path.parent.mkdir(parents=True, exist_ok=True)
    sub_path.write_text("print(1)")
    config_folder = Config(skip=["folder"])
    assert config_folder.is_skipped(sub_path) is True

    # Test skip_glob (singular setting name accepted by Config dataclass)
    config_glob = Config(skip_glob="*_me.py")
    assert config_glob.is_skipped(file_path) is True


def test_is_skipped_nonexistent_file(tmp_path):
    nonexistent = tmp_path / "does_not_exist.py"
    config = Config()
    assert config.is_skipped(nonexistent) is True


def test_is_skipped_gitignore(tmp_path):
    file_path = tmp_path / "file.py"
    file_path.write_text("print(1)")

    # 1. Test folder in git_ls_files (matching parents)
    config = Config(
        skip_gitignore=True,
        git_ls_files={tmp_path: [str(file_path.resolve())]}
    )
    assert config.is_skipped(file_path) is False

    # 2. Test fallback to _check_folder_git_ls_files branch (when folder not in git_ls_files keys)
    # Also ensure file is not a directory and doesn't exist in git_ls_files so it returns True (skipped)
    with patch.object(Config, "_check_folder_git_ls_files", return_value=tmp_path):
        config_fallback = Config(skip_gitignore=True, git_ls_files={tmp_path: []})
        assert config_fallback.is_skipped(file_path) is True

    # 3. Test git_folder found, but file is not in git_ls_files list
    config_not_in_list = Config(
        skip_gitignore=True,
        git_ls_files={tmp_path: [str(tmp_path / "other.py")]}
    )
    assert config_not_in_list.is_skipped(file_path) is True
