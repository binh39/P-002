# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

import pytest
from pathlib import Path
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config








def test_config_path_with_custom_config_object():
    # Covers branch where config is NOT DEFAULT_CONFIG, line 649 skipped because config is not DEFAULT_CONFIG
    path = Path("/some/path")
    custom_config = Config(line_length=100)
    cfg = _config(path=path, config=custom_config)
    assert cfg.line_length == 100


def test_config_kwargs_with_custom_config_raises_value_error():
    # Covers lines 652-655: config_kwargs is non-empty AND config is not DEFAULT_CONFIG
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=120)


def test_config_kwargs_only():
    # Covers lines 651, 658, 660: config_kwargs provided with DEFAULT_CONFIG
    cfg = _config(line_length=111)
    assert cfg.line_length == 111


def test_config_default_only():
    # Covers default return when path=None, config=DEFAULT_CONFIG, config_kwargs empty
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
