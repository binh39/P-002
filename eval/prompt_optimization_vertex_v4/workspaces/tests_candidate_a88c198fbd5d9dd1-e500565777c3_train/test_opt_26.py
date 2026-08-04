# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config








def test_config_with_custom_config_and_kwargs():
    # Tests that passing both a custom config and config_kwargs raises ValueError
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_cfg, line_length=120)


def test_config_with_custom_config_only():
    # Tests passing custom config without kwargs works
    custom_cfg = Config(line_length=100)
    cfg = _config(config=custom_cfg)
    assert cfg is custom_cfg


def test_config_with_kwargs_only():
    # Tests passing kwargs without custom config works
    cfg = _config(line_length=130)
    assert cfg.line_length == 130


def test_config_default():
    # Tests default values return DEFAULT_CONFIG
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
