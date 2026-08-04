# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_path_and_default_config(tmp_path):
    # Covers: path is truthy, config is DEFAULT_CONFIG, settings_path/file not in config_kwargs
    cfg = _config(path=tmp_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_with_settings_path_provided(tmp_path):
    # Covers: path is truthy, but "settings_path" is already in config_kwargs -> should not override
    p2 = tmp_path / "other"
    p2.mkdir()
    cfg = _config(path=tmp_path, settings_path=p2)
    assert cfg is not DEFAULT_CONFIG




def test_config_kwargs_with_non_default_config():
    # Covers: config_kwargs is truthy, but config is NOT DEFAULT_CONFIG -> raises ValueError
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=120)


def test_config_kwargs_with_default_config():
    # Covers: config_kwargs is truthy and config is DEFAULT_CONFIG -> creates new Config(**config_kwargs)
    cfg = _config(line_length=111)
    assert cfg.line_length == 111


def test_config_no_path_no_kwargs():
    # Covers: path is None/falsy, config_kwargs is empty -> returns default config as-is
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
