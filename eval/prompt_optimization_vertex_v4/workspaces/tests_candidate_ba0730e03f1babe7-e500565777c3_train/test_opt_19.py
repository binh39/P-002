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
    assert config_with_dir.is_skipped(file_path) is False

    # Test when self.directory is NOT in file_path.resolve().parents (else branch for file_name calculation)
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    config_without_dir = Config(directory=str(other_dir))
    assert config_without_dir.is_skipped(file_path) is False


def test_is_skipped_windows_drive_normalization(tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text("print(1)")

    # Use a custom Path subclass to simulate Windows drive letter normalization
    class MockPath(Path):
        def __str__(self):
            return "C:/path/to/file.py"
        def resolve(self, strict=False):
            return self

    mock_file = MockPath("C:/path/to/file.py")
    config_skip = Config(skip=["C:/path/to/file.py"])
    assert config_skip.is_skipped(mock_file) is True




def test_is_skipped_non_existent_file(tmp_path):
    # Lines 609-610: if not (os.path.isfile(os_path) or os.path.isdir(os_path) or os.path.islink(os_path)): return True
    fake_file = tmp_path / "does_not_exist.py"
    config = Config()
    assert config.is_skipped(fake_file) is True


