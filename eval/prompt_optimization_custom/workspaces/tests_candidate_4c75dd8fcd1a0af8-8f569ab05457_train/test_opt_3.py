# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 38], [38, 39], [38, 41]]}

import os
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from isort.settings import Config
from isort.files import find

@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.follow_links = True
    config.is_skipped.side_effect = lambda path: str(path).endswith('skip_this_dir')
    config.is_supported_filetype.side_effect = lambda filepath: filepath.endswith('.py')
    return config



def test_find_nonexistent_path(mock_config):
    paths = ['nonexistent_dir']
    skipped = []
    broken = []
    
    results = list(find(paths, mock_config, skipped, broken))
    
    assert len(results) == 0
    assert 'nonexistent_dir' in broken

def test_find_valid_file(mock_config):
    paths = ['test_file.py']
    skipped = []
    broken = []
    
    # Create a valid Python file
    with open('test_file.py', 'w') as f:
        f.write('print("Hello World")')
    
    results = list(find(paths, mock_config, skipped, broken))
    
    assert len(results) == 1
    assert results[0] == 'test_file.py'
    
    # Clean up
    os.remove('test_file.py')

