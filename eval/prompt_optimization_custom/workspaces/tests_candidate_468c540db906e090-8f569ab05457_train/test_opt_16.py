# file: src\sample_repo\isort\isort\settings.py:580-635
# asked: {"lines": [580, 582, 583, 585, 587, 589, 590, 591, 593, 594, 595, 597, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610, 612, 613, 614, 616, 618, 619, 620, 621, 622, 624, 629, 630, 631, 633, 635], "branches": [[582, 583], [582, 585], [590, 591], [590, 593], [593, 594], [593, 599], [594, 593], [594, 597], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 605], [606, 607], [609, 610], [609, 612], [612, 613], [612, 635], [613, 614], [613, 616], [619, 620], [619, 624], [620, 619], [620, 621], [628, 633], [628, 635]]}
# gained: {"lines": [580, 582, 585, 587, 589, 590, 593, 594, 595, 599, 600, 601, 602, 603, 605, 606, 607, 609, 610], "branches": [[582, 585], [590, 593], [593, 594], [593, 599], [594, 593], [600, 601], [600, 605], [601, 602], [601, 603], [605, 606], [605, 609], [606, 607], [609, 610]]}

import os
import pytest
from pathlib import Path
from isort.settings import Config

@pytest.fixture
def config_with_skips():
    return Config(
        directory='test_dir',
        skip_gitignore=True,
        git_ls_files={'folder': {'file1.py', 'file2.py'}}
    )

def test_is_skipped_directory(config_with_skips):
    file_path = Path('test_dir/skip_this_file.py')
    config_with_skips._skips = frozenset({'skip_this_file.py', 'skip_this_folder'})  # Use the private attribute
    assert config_with_skips.is_skipped(file_path) is True


def test_is_skipped_glob_pattern(config_with_skips):
    file_path = Path('test_dir/skip_this_file.skip')
    config_with_skips._skip_globs = frozenset({'*.skip'})  # Use the private attribute
    assert config_with_skips.is_skipped(file_path) is True

def test_is_skipped_non_existent_file(config_with_skips):
    file_path = Path('test_dir/non_existent_file.py')
    assert config_with_skips.is_skipped(file_path) is True

def test_is_skipped_gitignore(config_with_skips):
    file_path = Path('test_dir/.git')
    assert config_with_skips.is_skipped(file_path) is True


def test_is_skipped_git_ls_files_not_in_list(config_with_skips):
    file_path = Path('test_dir/file4.py')
    assert config_with_skips.is_skipped(file_path) is True
