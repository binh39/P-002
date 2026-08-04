# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default():
    # Covers: path is None, config is DEFAULT_CONFIG, no config_kwargs
    res = _config()
    assert res is DEFAULT_CONFIG


def test_config_path_adds_settings_path(tmp_path):
    # Covers: path provided (existing directory), config is DEFAULT_CONFIG, no settings_path/settings_file in kwargs
    res = _config(path=tmp_path)
    assert isinstance(res, Config)


def test_config_path_with_existing_settings_path_in_kwargs(tmp_path):
    # Covers: path provided, but "settings_path" is already in config_kwargs
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    res = _config(path=tmp_path, settings_path=other_dir)
    assert isinstance(res, Config)


def test_config_path_with_existing_settings_file_in_kwargs(tmp_path):
    # Covers: path provided, but "settings_file" is already in config_kwargs
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\nline_length = 88\n", encoding="utf-8")
    
    res = _config(path=tmp_path, settings_file=str(settings_file))
    assert isinstance(res, Config)
    assert res.line_length == 88


def test_config_kwargs_creates_new_config():
    # Covers: config_kwargs present, config is DEFAULT_CONFIG (lines 651, 658, 660)
    res = _config(line_length=100)
    assert isinstance(res, Config)
    assert res.line_length == 100


def test_config_kwargs_with_custom_config_raises_value_error():
    # Covers: config_kwargs present, and config is not DEFAULT_CONFIG -> raises ValueError (lines 651-653)
    custom_config = Config(line_length=120)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=100)
