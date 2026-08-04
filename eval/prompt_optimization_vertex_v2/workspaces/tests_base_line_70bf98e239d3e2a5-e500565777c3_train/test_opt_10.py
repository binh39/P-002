# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config






def test_config_with_kwargs_and_custom_config():
    # Covers lines 651-653: config_kwargs is non-empty and config is not DEFAULT_CONFIG -> raises ValueError
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=80)


def test_config_with_kwargs_and_default_config():
    # Covers lines 651, 658, 660: config_kwargs is non-empty and config is DEFAULT_CONFIG -> builds new Config
    cfg = _config(config=DEFAULT_CONFIG, line_length=88)
    assert cfg.line_length == 88


def test_config_no_path_no_kwargs():
    # Covers when path is None and config_kwargs is empty -> returns default config directly
    cfg = _config(path=None, config=DEFAULT_CONFIG)
    assert cfg is DEFAULT_CONFIG
