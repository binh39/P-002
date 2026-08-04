# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_path_and_default_config_no_settings_kwargs(tmp_path):
    # Covers:
    # - path is truthy
    # - config is DEFAULT_CONFIG
    # - "settings_path" not in config_kwargs
    # - "settings_file" not in config_kwargs
    # - config_kwargs becomes truthy because of settings_path = path
    # - config is DEFAULT_CONFIG (so no ValueError)
    # - config = Config(**config_kwargs) executed
    cfg = _config(path=tmp_path)
    assert isinstance(cfg, Config)


def test_config_path_with_settings_path_in_kwargs(tmp_path):
    # Covers path is truthy, but "settings_path" is already in config_kwargs,
    # so settings_path is not overwritten by path.
    # config_kwargs is truthy, config is DEFAULT_CONFIG -> creates new Config.
    cfg = _config(path=tmp_path, settings_path=tmp_path)
    assert isinstance(cfg, Config)


def test_config_path_with_settings_file_in_kwargs(tmp_path):
    # Covers path is truthy, but "settings_file" is already in config_kwargs,
    # so settings_path is not set from path.
    # config_kwargs is truthy, config is DEFAULT_CONFIG -> creates new Config.
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\nline_length = 79\n")
    cfg = _config(path=tmp_path, settings_file=str(settings_file))
    assert isinstance(cfg, Config)


def test_config_custom_config_and_config_kwargs_raises_value_error():
    # Covers:
    # - config_kwargs is truthy
    # - config is not DEFAULT_CONFIG
    # Raises ValueError ("You can either specify custom configuration options...")
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_cfg, line_length=80)


def test_config_custom_config_only():
    # Covers:
    # - config_kwargs is empty
    # - config is not DEFAULT_CONFIG
    # Returns config directly without modification.
    custom_cfg = Config(line_length=120)
    cfg = _config(config=custom_cfg)
    assert cfg is custom_cfg


def test_config_default_config_no_kwargs_no_path():
    # Covers:
    # - path is None (falsy)
    # - config_kwargs is empty (falsy)
    # - config is DEFAULT_CONFIG
    # Returns DEFAULT_CONFIG.
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
