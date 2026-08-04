# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import pytest
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Test when self.directory is set and Path(self.directory) in file_path.resolve().parents
    config = Config(directory=str(tmp_path))
    assert not config.is_skipped(file_path)

    # Test when self.directory is NOT set or not in parents
    config_no_dir = Config(directory="")
    assert not config_no_dir.is_skipped(file_path)




def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "glob_test.log"
    file_path.write_text("log")

    # Test skip_globs matching (lines 605-607)
    config = Config(skip_glob=["*.log"])
    assert config.is_skipped(file_path)


def test_is_skipped_non_existent_file(tmp_path):
    # Test lines 609-610: not (os.path.isfile(...) or os.path.isdir(...) or os.path.islink(...))
    fake_path = tmp_path / "does_not_exist.py"
    config = Config()
    assert config.is_skipped(fake_path)


def test_is_skipped_skip_gitignore(tmp_path, monkeypatch):
    file_path = tmp_path / "tracked.py"
    file_path.write_text("print(1)")

    resolved_path_str = str(file_path.resolve())
    folder_key = Path(tmp_path)

    config = Config(
        skip_gitignore=True,
        git_ls_files={folder_key: {resolved_path_str}}
    )

    # Case 1: any(folder in path.parents for path in file_paths) is True, and file is in git_ls_files -> not skipped
    assert not config.is_skipped(file_path)

    # Case 2: file NOT in git_ls_files -> skipped (returns True at line 633)
    untracked_file = tmp_path / "untracked.py"
    untracked_file.write_text("print(1)")
    config_untracked = Config(
        skip_gitignore=True,
        git_ls_files={folder_key: {resolved_path_str}}
    )
    assert config_untracked.is_skipped(untracked_file)

    # Case 3: folder not in any path.parents, falling through to _check_folder_git_ls_files (line 624)
    outside_path = tmp_path.parent / "outside.py"
    outside_path.write_text("print(1)")
    try:
        config_outside = Config(
            skip_gitignore=True,
            git_ls_files={folder_key: {resolved_path_str}}
        )
        monkeypatch.setattr(config_outside, "_check_folder_git_ls_files", lambda folder: folder_key)
        assert config_outside.is_skipped(outside_path)
    finally:
        if outside_path.exists():
            outside_path.unlink()
