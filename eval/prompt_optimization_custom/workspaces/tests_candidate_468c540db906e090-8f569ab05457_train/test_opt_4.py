# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}

import os
import pytest
from unittest.mock import patch, MagicMock
from isort.hooks import git_hook

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

def test_git_hook_no_files(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = []
    result = git_hook(strict=False)
    assert result == 0
    mock_get_lines.assert_called_once()

def test_git_hook_with_python_file(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['test.py']
    mock_get_output.return_value = 'import os\n\n'
    mock_api.check_code_string.return_value = False

    result = git_hook(strict=False, modify=False)
    assert result == 0
    mock_api.check_code_string.assert_called_once()
    mock_get_output.assert_called_once_with(['git', 'show', ':test.py'])

def test_git_hook_with_python_file_and_modify(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['test.py']
    mock_get_output.return_value = 'import os\n\n'
    mock_api.check_code_string.return_value = False

    result = git_hook(strict=False, modify=True)
    assert result == 0
    mock_api.sort_file.assert_called_once_with('test.py', config=mock_config.return_value)

def test_git_hook_strict_mode_with_errors(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['test.py']
    mock_get_output.return_value = 'import os\n\n'
    mock_api.check_code_string.return_value = False

    result = git_hook(strict=True, modify=False)
    assert result == 1
    mock_api.check_code_string.assert_called_once()

def test_git_hook_with_lazy_option(mock_get_lines, mock_get_output, mock_api, mock_config):
    mock_get_lines.return_value = ['test.py']
    mock_get_output.return_value = 'import os\n\n'
    mock_api.check_code_string.return_value = True

    result = git_hook(strict=False, modify=False, lazy=True)
    assert result == 0
    assert mock_get_lines.call_count == 1
    assert mock_api.check_code_string.call_count == 1
