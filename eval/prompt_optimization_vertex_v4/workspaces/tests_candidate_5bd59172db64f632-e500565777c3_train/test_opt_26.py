# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config




def test_config_path_provided_with_settings_path(tmp_path):
    # path is provided, but settings_path is already in config_kwargs (and exists)
    other_path = tmp_path / "other"
    other_path.mkdir()
    cfg = _config(path=tmp_path, settings_path=other_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_kwargs_with_non_default_config():
    # config_kwargs is non-empty AND config is not DEFAULT_CONFIG -> should raise ValueError
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=80)


def test_config_kwargs_with_default_config():
    # config_kwargs is non-empty AND config is DEFAULT_CONFIG -> should create Config(**config_kwargs)
    cfg = _config(line_length=120)
    assert cfg is not DEFAULT_CONFIG
    assert cfg.line_length == 120


def test_config_no_path_no_kwargs():
    # Neither path nor config_kwargs provided -> returns default config
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
