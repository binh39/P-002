# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default():
    # Covers: no path, config is DEFAULT_CONFIG, no config_kwargs -> returns DEFAULT_CONFIG
    cfg = _config()
    assert cfg is DEFAULT_CONFIG








def test_config_with_custom_config_and_kwargs_raises():
    # Covers: config_kwargs present, but config is NOT DEFAULT_CONFIG
    # -> raises ValueError
    custom_config = Config(line_length=80)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=100)


def test_config_with_custom_config_only():
    # Covers: config is NOT DEFAULT_CONFIG, config_kwargs is empty
    # -> returns custom config as-is
    custom_config = Config(line_length=80)
    cfg = _config(config=custom_config)
    assert cfg is custom_config
