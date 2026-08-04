# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_path_and_default_config(tmp_path):
    # Covers: path is truthy, config is DEFAULT_CONFIG, neither settings_path nor settings_file in config_kwargs
    cfg = _config(path=tmp_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_with_settings_path_provided(tmp_path):
    # Covers: path is truthy, but settings_path is already in config_kwargs
    custom_path = tmp_path / "sub"
    custom_path.mkdir()
    cfg = _config(path=tmp_path, settings_path=custom_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_path_with_settings_file_provided(tmp_path):
    # Covers: path is truthy, but settings_file is already in config_kwargs
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\nline_length = 88\n", encoding="utf-8")
    cfg = _config(path=tmp_path, settings_file=str(settings_file))
    assert cfg is not DEFAULT_CONFIG


def test_config_kwargs_with_non_default_config():
    # Covers: config_kwargs is truthy AND config is NOT DEFAULT_CONFIG -> raises ValueError
    custom_config = Config(line_length=88)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=79)


def test_config_kwargs_with_default_config():
    # Covers: config_kwargs is truthy AND config is DEFAULT_CONFIG -> creates new Config via kwargs
    cfg = _config(line_length=100)
    assert cfg.line_length == 100


def test_config_no_kwargs_non_default_config():
    # Covers: config_kwargs is empty, config is not DEFAULT_CONFIG
    custom_config = Config(line_length=88)
    cfg = _config(config=custom_config)
    assert cfg.line_length == 88
