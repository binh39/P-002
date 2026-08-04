# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config








def test_config_path_non_default_config():
    """Test when path is provided, but config is not DEFAULT_CONFIG."""
    path = Path("some_dummy_path")
    custom_config = Config(line_length=100)
    cfg = _config(path=path, config=custom_config)
    assert cfg == custom_config


def test_config_kwargs_with_non_default_config_raises_value_error():
    """Test that passing both config_kwargs and a non-default config raises ValueError."""
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=120)


def test_config_kwargs_with_default_config():
    """Test passing config_kwargs with DEFAULT_CONFIG (default)."""
    cfg = _config(line_length=110)
    assert cfg.line_length == 110


def test_config_no_args():
    """Test calling _config with no arguments."""
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
