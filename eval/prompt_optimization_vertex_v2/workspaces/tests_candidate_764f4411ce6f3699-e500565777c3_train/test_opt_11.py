# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 583, 585, 587, 589, 590, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610], "branches": [[582, 583], [582, 585], [590, 593], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610]]}

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from isort.settings import Config




def test_is_skipped_no_directory_and_path_traversal():
    file_path = Path("foo/bar/test.py")
    config = Config(directory="", skip=("foo",))
    assert config.is_skipped(file_path) is True


def test_is_skipped_skip_globs():
    file_path = Path("ignored_glob.py")
    config = Config(skip_glob=("*glob.py",))
    assert config.is_skipped(file_path) is True


def test_is_skipped_nonexistent_file():
    file_path = Path("does_not_exist.py")
    config = Config()
    assert config.is_skipped(file_path) is True


