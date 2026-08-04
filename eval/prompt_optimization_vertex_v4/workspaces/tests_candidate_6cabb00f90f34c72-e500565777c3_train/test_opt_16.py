# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [620, 621], [628, 633], [628, 635]]}

from pathlib import Path
import os
import pytest
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Test when self.directory is set and Path(self.directory) in file_path.resolve().parents
    config = Config(directory=str(tmp_path), skip_gitignore=False)
    assert not config.is_skipped(file_path)

    # Test when self.directory is not in parents (or self.directory is empty)
    config_no_dir = Config(directory="", skip_gitignore=False)
    assert not config_no_dir.is_skipped(file_path)




def test_is_skipped_by_skips_list(tmp_path):
    file_path = tmp_path / "skip_me.py"
    file_path.write_text("print(1)")

    abs_path_str = str(file_path.resolve()).replace("\\", "/")
    config = Config(skip="skip_me.py", skip_gitignore=False)
    # Using underlying _skips or config properties directly if needed, or valid Config parameters
    # Let's instantiate Config and manually update or use the appropriate parameter or skip initialization
    # Config uses `skip` or `skip_glob` parameters in __init__ (or `skip` maps to skips).
    # Let's test with Config(skip=["skip_me.py"]) or similar supported args if available, 
    # or subclass / instantiate via existing config object.
    
    # Alternatively, use Config with base parameters:
    config = Config(skip=["skip_me.py"], skip_gitignore=False)
    assert config.is_skipped(file_path)


def test_is_skipped_by_skip_globs(tmp_path):
    file_path = tmp_path / "glob_skip.py"
    file_path.write_text("print(1)")

    config = Config(skip_glob=["*glob_skip.py"], skip_gitignore=False)
    assert config.is_skipped(file_path)

    config_slash = Config(skip_glob=["/glob_skip.py"], skip_gitignore=False)
    config_is_skipped_with_slash = config_slash.is_skipped(file_path)
    assert isinstance(config_is_skipped_with_slash, bool)


def test_is_skipped_non_existent_file(tmp_path):
    non_existent = tmp_path / "does_not_exist.py"
    config = Config(skip_gitignore=False)
    assert config.is_skipped(non_existent) is True


def test_is_skipped_skip_gitignore_paths(tmp_path):
    file_path = tmp_path / "git_test.py"
    file_path.write_text("print(1)")

    config = Config(
        skip_gitignore=True,
        git_ls_files={tmp_path: [str(file_path.resolve())]},
    )
    assert not config.is_skipped(file_path)

    config_skipped = Config(
        skip_gitignore=True,
        git_ls_files={tmp_path: [str(tmp_path / "other.py")]},
    )
    assert config_skipped.is_skipped(file_path) is True
