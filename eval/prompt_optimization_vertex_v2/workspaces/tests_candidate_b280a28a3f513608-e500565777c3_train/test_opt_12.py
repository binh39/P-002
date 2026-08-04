# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 603, 605, 609, 610, 612, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 603], [605, 609], [609, 610], [609, 612], [612, 635]]}

from pathlib import Path
import os
from unittest.mock import patch
from isort.settings import Config


def test_is_skipped_directory_branch():
    # Use standard temporary directory handling via os and tempfile to avoid Windows tmp_path PermissionError locks
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        d = tmp_path / "sub"
        d.mkdir()
        f = d / "file.py"
        f.write_text("print(1)")

        # Test when self.directory is set and Path(self.directory) in file_path.resolve().parents
        config = Config(directory=str(tmp_path))
        assert not config.is_skipped(f)

        # Test when self.directory is not set or not in parents
        config_no_dir = Config(directory="")
        assert not config_no_dir.is_skipped(f)








def test_is_skipped_nonexistent_file():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        f = tmp_path / "does_not_exist.py"
        config = Config()
        assert config.is_skipped(f) is True


