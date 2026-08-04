# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

import pytest
from pathlib import Path
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default():
    # Covers when path is None, config is DEFAULT_CONFIG, no kwargs
    cfg = _config()
    assert cfg is DEFAULT_CONFIG






def test_config_path_with_settings_file_already_present(tmp_path):
    # Covers: path is truthy, but "settings_file" is already in config_kwargs
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\nline_length = 88\n", encoding="utf-8")
    p = tmp_path / "some"
    cfg = _config(path=p, settings_file=str(settings_file))
    assert cfg.line_length == 88


def test_config_kwargs_with_custom_config_raises_value_error():
    # Covers: config_kwargs is truthy, but config is NOT DEFAULT_CONFIG (raises ValueError)
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=80)


def test_config_kwargs_with_default_config():
    # Covers: config_kwargs is truthy, config is DEFAULT_CONFIG (creates new Config from kwargs)
    cfg = _config(line_length=79)
    assert cfg.line_length == 79
