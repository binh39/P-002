# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 133, 134, 147, 148, 149, 150, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 133], [134, 147], [148, 149], [150, 153], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from unittest.mock import patch, MagicMock
from isort.settings import Config
from isort.deprecated.finders import PathFinder

@pytest.fixture
def mock_config():
    return MagicMock(spec=Config)

@pytest.fixture
def mock_virtual_env(monkeypatch):
    monkeypatch.setenv("VIRTUAL_ENV", "/mock/venv")
    return "/mock/venv"

@pytest.fixture
def mock_conda_env(monkeypatch):
    monkeypatch.setenv("CONDA_PREFIX", "/mock/conda")
    return "/mock/conda"



def test_path_finder_with_stdlib_prefix(mock_config):
    mock_config.virtual_env = None
    mock_config.conda_env = None
    path_finder = PathFinder(config=mock_config, path="D:\\mock\\path")

    stdlib_prefix = os.path.normcase(sysconfig.get_paths()["stdlib"])
    assert stdlib_prefix in path_finder.paths

def test_path_finder_with_system_paths(mock_config):
    mock_config.virtual_env = None
    mock_config.conda_env = None
    path_finder = PathFinder(config=mock_config, path="D:\\mock\\path")

    # Mocking sys.path to include a system path
    original_sys_path = sys.path.copy()
    sys.path.append("D:\\mock\\system\\path")
    
    path_finder = PathFinder(config=mock_config, path="D:\\mock\\path")
    
    assert "D:\\mock\\system\\path" in path_finder.paths

    # Clean up
    sys.path = original_sys_path
