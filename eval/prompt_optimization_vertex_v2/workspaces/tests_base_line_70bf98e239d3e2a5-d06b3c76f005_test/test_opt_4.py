# file: src\sample_repo\isort\isort\settings.py:754-786
# asked: {"lines": [754, 755, 756, 757, 758, 759, 760, 762, 763, 764, 766, 767, 768, 769, 771, 772, 773, 775, 776, 777, 779, 780, 781, 783, 784, 786], "branches": [[757, 758], [757, 786], [758, 759], [758, 775], [760, 758], [760, 761], [772, 758], [772, 773], [775, 776], [775, 779], [776, 775], [776, 777], [780, 781], [780, 783]]}
# gained: {"lines": [754, 755, 756, 757, 758, 759, 760, 762, 763, 764, 766, 767, 768, 769, 771, 772, 775, 776, 777, 779, 780, 781, 783, 784, 786], "branches": [[757, 758], [758, 759], [758, 775], [760, 758], [760, 761], [772, 758], [775, 776], [775, 779], [776, 775], [776, 777], [780, 781], [780, 783]]}

import os
import tempfile
import pytest
from isort.settings import _find_config

@pytest.fixture
def custom_tmp_path():
    d = tempfile.mkdtemp()
    try:
        yield d
    finally:
        # Clean up properly, ignoring permission errors if any files are locked
        import shutil
        shutil.rmtree(d, ignore_errors=True)

def test_find_config_success(custom_tmp_path):
    # Test finding a config file successfully
    config_file = os.path.join(custom_tmp_path, ".editorconfig")
    with open(config_file, "w") as f:
        f.write("root = true")
    
    dir_path, config_data = _find_config(custom_tmp_path)
    assert dir_path == custom_tmp_path
    assert isinstance(config_data, dict)

def test_find_config_exception_in_get_config_data(custom_tmp_path, monkeypatch):
    # Test when config file exists but reading it raises an exception (e.g., malformed TOML/INI)
    config_file = os.path.join(custom_tmp_path, "setup.cfg")
    with open(config_file, "w") as f:
        f.write("invalid content")
    
    # Force _get_config_data to raise an exception for this file
    import isort.settings
    def mock_get_config_data(*args, **kwargs):
        raise RuntimeError("Bad config")
    
    monkeypatch.setattr(isort.settings, "_get_config_data", mock_get_config_data)
    
    dir_path, config_data = _find_config(custom_tmp_path)
    assert dir_path == custom_tmp_path
    assert config_data == {}

def test_find_config_stop_dir(custom_tmp_path):
    # Test stopping search when encountering a stop dir like .git
    sub_dir = os.path.join(custom_tmp_path, "sub")
    os.mkdir(sub_dir)
    
    git_dir = os.path.join(custom_tmp_path, ".git")
    os.mkdir(git_dir)
    
    dir_path, config_data = _find_config(sub_dir)
    assert dir_path == custom_tmp_path
    assert config_data == {}

def test_find_config_max_depth_or_root(custom_tmp_path):
    # Test reaching root or max depth without finding config or stop dir
    sub_dir = os.path.join(custom_tmp_path, "a", "b")
    os.makedirs(sub_dir)
    
    dir_path, config_data = _find_config(sub_dir)
    assert dir_path == sub_dir
    assert config_data == {}
