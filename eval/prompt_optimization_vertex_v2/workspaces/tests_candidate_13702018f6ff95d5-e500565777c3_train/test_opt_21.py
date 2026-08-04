# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config






def test_config_with_kwargs_and_custom_config_raises_value_error():
    # Covers lines 651-654: config_kwargs is non-empty and config is NOT DEFAULT_CONFIG
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=80)


def test_config_with_only_kwargs():
    # Covers lines 658-660: config_kwargs is non-empty, config is DEFAULT_CONFIG
    cfg = _config(line_length=88)
    assert cfg.line_length == 88


def test_config_with_no_kwargs_and_custom_config():
    # Covers branch where config_kwargs is empty, returning custom config directly
    custom_config = Config(line_length=120)
    cfg = _config(config=custom_config)
    assert cfg.line_length == 120
