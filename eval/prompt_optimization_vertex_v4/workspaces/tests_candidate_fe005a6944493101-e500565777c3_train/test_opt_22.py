# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 635]]}

import os
import posixpath
from pathlib import Path
from unittest.mock import MagicMock
from isort.settings import Config


def test_is_skipped_directory_handling(tmp_path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    file_path = sub_dir / "file.py"
    file_path.write_text("print(1)")

    config1 = Config(directory=str(tmp_path))
    assert config1.is_skipped(file_path) is False

    config2 = Config(directory="")
    assert config2.is_skipped(file_path) is False


def test_is_skipped_windows_drive_normalization(tmp_path):
    file_path = tmp_path / "file.py"
    file_path.write_text("print(1)")

    class MockConfig(Config):
        @property
        def skips(self):
            return frozenset(["C:/file.py", "file.py"])

    cfg = MockConfig(directory=str(tmp_path))

    class FakePath(Path):
        def __str__(self):
            return "C:\\file.py"
        
        def resolve(self, strict=False):
            return self

    fp = FakePath("C:/file.py")
    assert cfg.is_skipped(fp) is True




def test_is_skipped_skip_globs(tmp_path):
    file_path = tmp_path / "foo" / "bar.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("print(1)")

    config_glob1 = Config(skip_glob=["*bar.py"])
    assert config_glob1.is_skipped(file_path) is True

    config_glob2 = Config(skip_glob=["*/foo/*"])
    assert config_glob2.is_skipped(file_path) is True

    config_glob_no = Config(skip_glob=["nonexistent*"])
    assert config_glob_no.is_skipped(file_path) is False


def test_is_skipped_nonexistent_file(tmp_path):
    non_existent = tmp_path / "does_not_exist.py"
    config = Config()
    assert config.is_skipped(non_existent) is True


