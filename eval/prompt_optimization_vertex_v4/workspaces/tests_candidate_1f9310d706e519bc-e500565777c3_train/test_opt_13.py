# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 603, 605, 609, 610, 612, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 603], [605, 609], [609, 610], [609, 612], [612, 635]]}

from pathlib import Path
import os
from unittest.mock import patch
from isort.settings import Config


def test_is_skipped_directory_branch(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "test.py"
    file_path.write_text("print(1)")

    # Test when self.directory is set and Path(self.directory) is in file_path.resolve().parents
    config_with_dir = Config(directory=str(tmp_path))
    assert not config_with_dir.is_skipped(file_path)

    # Test when self.directory is not set (falls to else: file_name = str(file_path))
    config_without_dir = Config(directory="")
    assert not config_without_dir.is_skipped(file_path)


def test_is_skipped_windows_drive_path(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")
    config = Config()

    with patch("os.path.isfile", return_value=True), patch("os.path.isdir", return_value=False), patch("os.path.islink", return_value=False):
        # Mock normalized_path to start with C: to hit `if normalized_path[1:2] == ":":`
        with patch("pathlib.Path.resolve", return_value=file_path):
            original_str = str
            def mock_str(obj):
                if obj == file_path:
                    return "C:/some/path/test.py"
                return original_str(obj)
            with patch("isort.settings.str", side_effect=mock_str):
                assert not config.is_skipped(file_path)




def test_is_skipped_not_a_file_dir_link(tmp_path):
    file_path = tmp_path / "nonexistent.py"
    config = Config()

    # Ensure isfile, isdir, islink all return False so it returns True (skipped)
    with patch("os.path.isfile", return_value=False), \
         patch("os.path.isdir", return_value=False), \
         patch("os.path.islink", return_value=False):
        assert config.is_skipped(file_path)


