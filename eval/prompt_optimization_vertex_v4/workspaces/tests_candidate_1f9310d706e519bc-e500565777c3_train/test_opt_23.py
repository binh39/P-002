# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_path_default_config_no_settings_kwargs(tmp_path: Path):
    """Test when path is provided, config is DEFAULT_CONFIG, and neither settings_path nor settings_file are in config_kwargs.
    This triggers line 649 (setting config_kwargs['settings_path'] = path) and then lines 651-658 (creating a new Config from config_kwargs).
    """
    cfg = _config(path=tmp_path)
    # The config should look for configuration inside tmp_path (which has no config file, so it falls back to defaults or sets path_root/directory)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_provided_but_settings_path_in_kwargs(tmp_path: Path):
    """Test when path is provided, but 'settings_path' is already in config_kwargs.
    This bypasses line 649, but hits config_kwargs (lines 651-658).
    """
    other_path = tmp_path / "sub"
    other_path.mkdir()
    cfg = _config(path=tmp_path, settings_path=other_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_provided_but_settings_file_in_kwargs(tmp_path: Path):
    """Test when path is provided, but 'settings_file' is in config_kwargs.
    This bypasses line 649, but hits config_kwargs (lines 651-658).
    """
    settings_file = tmp_path / "pyproject.toml"
    settings_file.write_text("[tool.isort]\nprofile = \"black\"\n")
    cfg = _config(path=tmp_path, settings_file=str(settings_file))
    assert cfg is not DEFAULT_CONFIG


def test_config_kwargs_with_non_default_config_raises_value_error():
    """Test that passing both a custom config object and config_kwargs raises a ValueError.
    This hits lines 651-656 (raising ValueError).
    """
    custom_config = Config()
    with pytest.raises(
        ValueError,
        match="You can either specify custom configuration options using kwargs or passing in a Config object. Not Both!",
    ):
        _config(config=custom_config, profile="black")


def test_config_no_kwargs_non_default_config():
    """Test passing a custom config object without any config_kwargs.
    This bypasses config_kwargs (lines 651-658) and directly returns the config.
    """
    custom_config = Config()
    cfg = _config(config=custom_config)
    assert cfg is custom_config
