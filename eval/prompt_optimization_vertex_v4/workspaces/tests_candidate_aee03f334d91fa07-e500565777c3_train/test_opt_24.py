# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_path_default_config_no_settings_kwargs(tmp_path):
    """Test when path is provided, config is DEFAULT_CONFIG, and neither settings_path nor settings_file are in config_kwargs."""
    cfg = _config(path=tmp_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_provided_with_settings_path(tmp_path):
    """Test when path is provided, but settings_path is already in config_kwargs."""
    other_path = tmp_path / "other"
    other_path.mkdir()
    cfg = _config(path=tmp_path, settings_path=other_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_kwargs_with_non_default_config():
    """Test that passing both a custom config object and config_kwargs raises ValueError."""
    custom_config = Config(line_length=80)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=100)


def test_config_kwargs_with_default_config():
    """Test passing config_kwargs along with default config."""
    cfg = _config(config=DEFAULT_CONFIG, line_length=99)
    assert cfg.line_length == 99


def test_config_no_path_no_kwargs():
    """Test with no path and no kwargs returns the config as-is."""
    cfg = _config(config=DEFAULT_CONFIG)
    assert cfg is DEFAULT_CONFIG
