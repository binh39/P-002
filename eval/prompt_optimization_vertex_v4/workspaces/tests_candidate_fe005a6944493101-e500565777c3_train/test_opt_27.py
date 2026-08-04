# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_defaults():
    # Covers when path is None, config is DEFAULT_CONFIG, config_kwargs is empty
    cfg = _config()
    assert cfg is DEFAULT_CONFIG


def test_config_path_default_config(tmp_path):
    # Covers when path is provided, config is DEFAULT_CONFIG, and neither settings_path nor settings_file in config_kwargs
    cfg = _config(path=tmp_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_with_settings_path(tmp_path):
    # Covers when path is provided, but "settings_path" is already in config_kwargs
    explicit_p = tmp_path / "other"
    explicit_p.mkdir()
    cfg = _config(path=tmp_path, settings_path=explicit_p)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_with_settings_file(tmp_path):
    # Covers when path is provided, but "settings_file" is already in config_kwargs
    cfg_file = tmp_path / "setup.cfg"
    cfg_file.write_text("[isort]\nline_length = 88")
    cfg = _config(path=tmp_path, settings_file=str(cfg_file))
    assert cfg is not DEFAULT_CONFIG
    assert cfg.line_length == 88


def test_config_path_with_custom_config_object(tmp_path):
    # Covers when path is provided, but config is not DEFAULT_CONFIG
    custom_config = Config(line_length=88)
    cfg = _config(path=tmp_path, config=custom_config)
    assert cfg is custom_config


def test_config_kwargs_with_custom_config_raises():
    # Covers raising ValueError when config_kwargs is non-empty and config is not DEFAULT_CONFIG
    custom_config = Config(line_length=88)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=100)


def test_config_kwargs_with_default_config():
    # Covers config_kwargs is non-empty and config is DEFAULT_CONFIG (creates new Config)
    cfg = _config(line_length=99)
    assert cfg.line_length == 99
    assert cfg is not DEFAULT_CONFIG
