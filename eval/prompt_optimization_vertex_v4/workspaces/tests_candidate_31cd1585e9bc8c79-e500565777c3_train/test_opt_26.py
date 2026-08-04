# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_with_path_and_default_config(tmp_path):
    # Covers line 644-649 (path is truthy, config is DEFAULT_CONFIG, no settings_path/settings_file in kwargs)
    # Also covers lines 651 and 658, 660 using a real existing temp directory
    cfg = _config(path=tmp_path, config=DEFAULT_CONFIG)
    assert cfg is not DEFAULT_CONFIG


def test_config_with_path_and_existing_settings_path(tmp_path):
    # Covers condition where "settings_path" is already in config_kwargs
    other_path = tmp_path / "other"
    other_path.mkdir()
    path = tmp_path / "some"
    path.mkdir()
    cfg = _config(path=path, config=DEFAULT_CONFIG, settings_path=other_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_with_path_and_existing_settings_file(tmp_path):
    # Covers condition where "settings_file" is already in config_kwargs using a real file
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\nline_length = 88")
    path = tmp_path / "some"
    path.mkdir()
    cfg = _config(path=path, config=DEFAULT_CONFIG, settings_file=str(settings_file))
    assert cfg.line_length == 88


def test_config_with_custom_config_and_kwargs_raises():
    # Covers lines 652-656: config is not DEFAULT_CONFIG and config_kwargs is truthy -> raises ValueError
    custom_cfg = Config()
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_cfg, line_length=100)


def test_config_default_no_kwargs():
    # Covers when path is None, config is DEFAULT_CONFIG, config_kwargs is empty
    cfg = _config(path=None, config=DEFAULT_CONFIG)
    assert cfg is DEFAULT_CONFIG
