# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def not_default_config_instance() -> Config:
    return Config(line_length=100)


def test_config_default_no_args():
    # Covers: default path (None), default config, no config_kwargs
    res = _config()
    assert res is DEFAULT_CONFIG


def test_config_with_path_and_default_config(tmp_path):
    # Covers lines 644-649: path is provided, config is DEFAULT_CONFIG, no settings_path/file in kwargs
    res = _config(path=tmp_path)
    assert isinstance(res, Config)


def test_config_with_path_and_existing_settings_path(tmp_path):
    # Covers line 644-647 condition where "settings_path" is already in config_kwargs
    other_path = tmp_path / "subdir"
    other_path.mkdir()
    res = _config(path=tmp_path, settings_path=other_path)
    assert isinstance(res, Config)


def test_config_with_path_and_existing_settings_file(tmp_path):
    # Covers line 644-647 condition where "settings_file" is already in config_kwargs
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\n", encoding="utf-8")
    res = _config(path=tmp_path, settings_file=str(settings_file))
    assert isinstance(res, Config)


def test_config_with_custom_config_and_kwargs_raises_error():
    # Covers lines 652-656: config_kwargs is truthy AND config is not DEFAULT_CONFIG
    custom_cfg = not_default_config_instance()
    with pytest.raises(ValueError) as excinfo:
        _config(config=custom_cfg, line_length=120)
    assert "You can either specify custom configuration options using kwargs" in str(excinfo.value)


def test_config_with_kwargs_only():
    # Covers lines 658-660: config_kwargs is truthy and config is DEFAULT_CONFIG
    res = _config(line_length=111)
    assert isinstance(res, Config)
    assert res.line_length == 111
