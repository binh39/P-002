# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
import pytest
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "file.py"
    file_path.write_text("# content")

    # Config with directory set to sub_dir (parents check)
    config = Config(directory=str(sub_dir))
    assert not config.is_skipped(file_path)

    # Config without directory set (exercises the 'else' branch of line 582)
    config_no_dir = Config(settings_path=str(tmp_path))
    assert not config_no_dir.is_skipped(file_path)


def test_is_skipped_windows_drive_normalization(tmp_path):
    test_file = tmp_path / "test_drive.py"
    test_file.write_text("print(1)")

    config = Config()

    class FakePath(Path):
        def __str__(self):
            s = str(test_file)
            # Replace drive letter or prefix to have colon at index 1, e.g. "C:/"
            if len(s) > 1 and s[1] == ":":
                return s
            return "C:" + s

    fake_p = FakePath(test_file)
    assert not config.is_skipped(fake_p)




def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "skip_me.py"
    file_path.write_text("# content")

    config = Config(skip_glob=("*skip_me*",))
    assert config.is_skipped(file_path)


def test_is_skipped_nonexistent_file(tmp_path):
    nonexistent = tmp_path / "does_not_exist.py"
    config = Config()
    # Lines 609-610: not (os.path.isfile or os.path.isdir or os.path.islink) -> returns True
    assert config.is_skipped(nonexistent)


def test_is_skipped_skip_gitignore(tmp_path):
    file_path = tmp_path / "file.py"
    file_path.write_text("# content")

    resolved_file = str(file_path.resolve())
    
    # Case 1: file not in git_ls_files -> skipped
    config = Config(skip_gitignore=True, git_ls_files={Path(tmp_path): {resolved_file + "_other"}})
    config._check_folder_git_ls_files = lambda folder: Path(tmp_path)
    assert config.is_skipped(file_path)

    # Case 2: file is in git_ls_files -> not skipped
    config2 = Config(skip_gitignore=True, git_ls_files={Path(tmp_path): {resolved_file}})
    config2._check_folder_git_ls_files = lambda folder: Path(tmp_path)
    assert not config2.is_skipped(file_path)
