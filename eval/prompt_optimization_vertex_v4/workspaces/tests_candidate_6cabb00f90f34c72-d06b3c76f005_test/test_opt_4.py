# file: src\sample_repo\isort\isort\settings.py:754-786
# asked: {"lines": [754, 755, 756, 757, 758, 759, 760, 762, 763, 764, 766, 767, 768, 769, 771, 772, 773, 775, 776, 777, 779, 780, 781, 783, 784, 786], "branches": [[757, 758], [757, 786], [758, 759], [758, 775], [760, 758], [760, 761], [772, 758], [772, 773], [775, 776], [775, 779], [776, 775], [776, 777], [780, 781], [780, 783]]}
# gained: {"lines": [754, 755, 756, 757, 758, 759, 760, 762, 763, 764, 766, 767, 768, 769, 771, 772, 773, 775, 776, 777, 779, 780, 781, 783, 784, 786], "branches": [[757, 758], [758, 759], [758, 775], [760, 758], [760, 761], [772, 758], [772, 773], [775, 776], [775, 779], [776, 775], [776, 777], [780, 781], [780, 783]]}

import os
import tempfile
import pytest
from isort.settings import _find_config

def test_find_config_success_and_exception():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a valid config file first to test successful return
        config_name = ".isort.cfg"
        config_path = os.path.join(tmpdir, config_name)
        with open(config_path, "w") as f:
            f.write("[isort]\nline_length = 88\n")
        
        # Test finding valid config
        directory, data = _find_config(tmpdir)
        assert directory == tmpdir
        assert "line_length" in data or bool(data)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test exception handling when reading a malformed config or file that causes an error
        config_name = "setup.cfg"
        config_path = os.path.join(tmpdir, config_name)
        with open(config_path, "w") as f:
            f.write("invalid content that might raise or fail config parsing if section is wrong or file is bad")
        
        # Depending on how _get_config_data behaves, we can also patch it or create a condition
        # where _get_config_data raises an exception.
        import isort.settings
        original_get_config_data = isort.settings._get_config_data

        def mock_get_config_data(path, section):
            raise ValueError("Intentional parse failure")

        isort.settings._get_config_data = mock_get_config_data
        try:
            with pytest.warns(UserWarning, match="Failed to pull configuration information"):
                directory, data = _find_config(tmpdir)
            assert directory == tmpdir
            assert data == {}
        finally:
            isort.settings._get_config_data = original_get_config_data

def test_find_config_stop_dir_and_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a stop search directory inside tmpdir, e.g., ".git"
        stop_dir_name = ".git"
        os.makedirs(os.path.join(tmpdir, stop_dir_name))

        # Ensure no config files exist, so it hits STOP_CONFIG_SEARCH_ON_DIRS
        directory, data = _find_config(tmpdir)
        assert directory == tmpdir
        assert data == {}

    # Test fallback when no config and no stop dir reaches root or max depth / loop finish
    with tempfile.TemporaryDirectory() as tmpdir:
        sub_dir = os.path.join(tmpdir, "a", "b")
        os.makedirs(sub_dir)
        directory, data = _find_config(sub_dir)
        assert directory == sub_dir
        assert data == {}
