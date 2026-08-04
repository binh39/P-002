# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_defaults():
    # 1. path is None, config is DEFAULT_CONFIG, no config_kwargs -> covers nothing in the if statements
    cfg = _config()
    assert cfg is DEFAULT_CONFIG






def test_config_kwargs_with_custom_config_raises():
    # config_kwargs provided AND custom config provided -> raises ValueError
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_cfg, line_length=80)


def test_config_kwargs_with_default_config():
    # config_kwargs provided, config is DEFAULT_CONFIG -> creates new Config object from kwargs
    cfg = _config(line_length=88)
    assert cfg.line_length == 88
    assert cfg is not DEFAULT_CONFIG
