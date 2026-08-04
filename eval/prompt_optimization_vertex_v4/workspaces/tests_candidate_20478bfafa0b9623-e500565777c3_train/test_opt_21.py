# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 616, 618, 619, 620, 621, 622, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 616], [619, 620], [620, 621], [628, 633], [628, 635]]}

import os
from pathlib import Path
import pytest
from isort.settings import Config




def test_is_skipped_position_loop(tmp_path):
    # Tests lines 599-603: while position[1]: checking parents against self.skips
    file_path = tmp_path / "a" / "b" / "file.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("x")

    class CustomConfig(Config):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "_skips", frozenset(["b"]))

    config = CustomConfig()
    assert config.is_skipped(file_path) is True

    config_no_skip = Config()
    assert config_no_skip.is_skipped(file_path) is False


def test_is_skipped_skip_globs(tmp_path):
    # Tests lines 605-607: skip_globs matching
    file_path = tmp_path / "test_module.py"
    file_path.write_text("x")

    class CustomConfig(Config):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "_skip_globs", frozenset(["*_module.py"]))

    config = CustomConfig()
    assert config.is_skipped(file_path) is True

    class CustomConfigSlash(Config):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "_skip_globs", frozenset(["/test_module.py"]))

    config_slash = CustomConfigSlash()
    # When file_name is absolute path or relative, fnmatch checks file_name and "/" + file_name.
    # If file_name is absolute path (str(file_path)), "/" + file_name starts with "//" unless handled or relative.
    # Let's test with a relative file_path or directory set so file_name doesn't start with drive letter.
    config_slash_dir = CustomConfigSlash(directory=str(tmp_path))
    assert config_slash_dir.is_skipped(file_path) is True


def test_is_skipped_non_existent_file(tmp_path):
    # Tests lines 609-610: not (os.path.isfile(...) or os.path.isdir(...) or os.path.islink(...))
    fake_path = tmp_path / "does_not_exist.py"
    config = Config()
    assert config.is_skipped(fake_path) is True


def test_is_skipped_skip_gitignore_paths(tmp_path):
    # Tests lines 612-633: skip_gitignore logic
    file_path = tmp_path / "script.py"
    file_path.write_text("x")

    class CustomConfig(Config):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "git_ls_files", {tmp_path: [str(file_path.resolve())]})

        def _check_folder_git_ls_files(self, folder: str):
            return None

    config = CustomConfig(skip_gitignore=True)
    assert config.is_skipped(file_path) is False

    class CustomConfigNoMatch(Config):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "git_ls_files", {tmp_path: [str(tmp_path / "other.py")]})

        def _check_folder_git_ls_files(self, folder: str):
            return tmp_path

    config_no_match = CustomConfigNoMatch(skip_gitignore=True)
    assert config_no_match.is_skipped(file_path) is True


def test_is_skipped_returns_false(tmp_path):
    # Test final return False at line 635
    file_path = tmp_path / "normal.py"
    file_path.write_text("x")
    config = Config()
    assert config.is_skipped(file_path) is False
