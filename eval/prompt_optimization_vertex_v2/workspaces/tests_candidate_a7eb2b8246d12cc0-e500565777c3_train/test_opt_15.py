# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 635], "branches": [[582, 583], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 635]]}

from pathlib import Path
import os
import pytest
from unittest.mock import patch, PropertyMock
from isort.settings import Config


def test_is_skipped_with_directory_and_windows_path(monkeypatch):
    d = Path(os.path.abspath("test_project_dir"))
    d.mkdir(exist_ok=True)
    sub_file = d / "sub" / "file.py"
    sub_file.parent.mkdir(exist_ok=True, parents=True)
    sub_file.write_text("print(1)")

    try:
        config = Config(
            directory=str(d),
            skip=("sub/file.py", "parent_skip"),
            skip_glob=("*.txt", "/glob_match.py"),
            skip_gitignore=True,
        )

        with patch("pathlib.Path.resolve", return_value=sub_file.resolve()):
            with patch("os.path.relpath", return_value=os.path.relpath(sub_file.resolve(), d)):
                non_existent = d / "does_not_exist.py"
                assert config.is_skipped(non_existent) is True
    finally:
        try:
            for root, dirs, files in os.walk(d, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(d)
        except Exception:
            pass




def test_is_skipped_skips_and_globs_branches(monkeypatch):
    d = Path(os.path.abspath("test_proj"))
    d.mkdir(exist_ok=True)
    
    try:
        config = Config(
            skip=("absolute_skip.py", "folder_skip"),
            skip_glob=("*.log", "/absolute_glob.py"),
            skip_gitignore=False,
        )

        f = d / "absolute_skip.py"
        f.write_text("")
        
        skipped_nested = d / "folder_skip" / "inner.py"
        skipped_nested.parent.mkdir(exist_ok=True, parents=True)
        skipped_nested.write_text("")
        assert config.is_skipped(skipped_nested) is True

        glob_file = d / "test.log"
        glob_file.write_text("")
        assert config.is_skipped(glob_file) is True

        normal_file = d / "normal.py"
        normal_file.write_text("")
        assert config.is_skipped(normal_file) is False
    finally:
        try:
            for root, dirs, files in os.walk(d, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(d)
        except Exception:
            pass
