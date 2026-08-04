# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 65, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 65], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 80], [84, 87], [88, 77], [88, 89]]}

import os
import pytest
from unittest.mock import patch, MagicMock
from isort.hooks import git_hook
from isort.exceptions import FileSkipped  # Import the exceptions

@pytest.fixture
def mock_get_lines():
    with patch('isort.hooks.get_lines') as mock:
        yield mock

@pytest.fixture
def mock_get_output():
    with patch('isort.hooks.get_output') as mock:
        yield mock

@pytest.fixture
def mock_api():
    with patch('isort.hooks.api') as mock:
        yield mock

@pytest.fixture
def mock_config():
    with patch('isort.hooks.Config') as mock:
        yield mock

def test_git_hook_no_files(mock_get_lines):
    mock_get_lines.return_value = []
    result = git_hook(strict=False)
    assert result == 0
    mock_get_lines.assert_called_once()

def test_git_hook_with_python_file(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['test_file.py']
    mock_get_output.return_value = 'import os\n\n# some code\n'
    mock_api.check_code_string.return_value = False  # Simulate a failure
    mock_api.sort_file = MagicMock()  # Mock the sort_file method

    result = git_hook(strict=False, modify=True)

    assert result == 0
    mock_api.check_code_string.assert_called_once()
    mock_api.sort_file.assert_called_once_with('test_file.py', config=mock_config.return_value)

def test_git_hook_with_skipped_file(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['skipped_file.py']
    mock_get_output.return_value = 'import os\n\n# some code\n'
    
    # Simulate a skipped file by raising the exception with required arguments
    mock_api.check_code_string.side_effect = FileSkipped("File skipped", "skipped_file.py")

    result = git_hook(strict=False)

    assert result == 0
    mock_api.check_code_string.assert_called_once()

def test_git_hook_strict_mode_with_errors(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['error_file.py']
    mock_get_output.return_value = 'import os\n\n# some code\n'
    mock_api.check_code_string.return_value = False  # Simulate a failure

    result = git_hook(strict=True)

    assert result == 1
    mock_api.check_code_string.assert_called_once()

def test_git_hook_with_no_modify(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['test_file.py']
    mock_get_output.return_value = 'import os\n\n# some code\n'
    mock_api.check_code_string.return_value = False  # Simulate a failure

    result = git_hook(strict=False, modify=False)

    assert result == 0
    mock_api.sort_file.assert_not_called()
