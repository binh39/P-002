# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 603, 605, 606, 607, 609, 610, 612, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 635]]}

from pathlib import Path
import os
from unittest.mock import patch
from isort.settings import Config

def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Test when self.directory is set and contains file_path in parents
    config = Config(directory=str(tmp_path), skip_gitignore=False)
    assert config.is_skipped(file_path) is False

    # Test when self.directory is NOT set or does not contain file_path in parents
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    config_no_dir = Config(directory=str(other_dir), skip_gitignore=False)
    assert config_no_dir.is_skipped(file_path) is False

def test_is_skipped_windows_drive_prefix(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")

    config = Config(skip_gitignore=False)
    with patch("isort.settings.str") as mock_str:
        # Mock str(file_path) to simulate a Windows path with a drive letter, e.g. "C:\\test.py"
        def side_effect(obj):
            if obj is file_path:
                return "C:\\test.py"
            return str(obj)
        mock_str.side_effect = side_effect
        # Ensure os.path.isfile/isdir/islink returns True for this fake path so we don't trigger line 609
        with patch("os.path.isfile", return_value=True):
            assert config.is_skipped(file_path) is False


def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "glob_me.py"
    file_path.write_text("print(1)")

    # Match via skip_globs (lines 605-607)
    config = Config(skip_glob=frozenset(["*_me.py"]), skip_gitignore=False)
    assert config.is_skipped(file_path) is True

def test_is_skipped_non_existent_file(tmp_path):
    file_path = tmp_path / "non_existent.py"
    # Do not create the file, so isfile, isdir, islink all return False (lines 609-610)

    config = Config(skip_gitignore=False)
    assert config.is_skipped(file_path) is True

