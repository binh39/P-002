# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default():
    """Test calling _config with default parameters."""
    cfg = _config()
    assert cfg is DEFAULT_CONFIG








def test_config_with_custom_config_and_kwargs_raises():
    """Test that passing both a non-default config and config_kwargs raises ValueError."""
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=120)


def test_config_with_only_kwargs():
    """Test passing config_kwargs with default config creates a new Config object."""
    cfg = _config(line_length=120)
    assert cfg is not DEFAULT_CONFIG
    assert cfg.line_length == 120
