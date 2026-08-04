# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

import pytest
from pathlib import Path
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default_no_path_no_kwargs():
    # path=None, config=DEFAULT_CONFIG, no kwargs
    res = _config()
    assert res is DEFAULT_CONFIG








def test_config_with_path_custom_config():
    # path provided, but config is NOT DEFAULT_CONFIG
    custom_cfg = Config(line_length=100)
    res = _config(path=Path("."), config=custom_cfg)
    assert res is custom_cfg


def test_config_kwargs_with_custom_config_raises_value_error():
    # config_kwargs is non-empty AND config is not DEFAULT_CONFIG
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_cfg, line_length=120)


def test_config_kwargs_with_default_config():
    # config_kwargs is non-empty AND config is DEFAULT_CONFIG
    res = _config(line_length=111)
    assert res is not DEFAULT_CONFIG
    assert res.line_length == 111
