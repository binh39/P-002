# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config






def test_config_with_path_and_existing_settings_file(monkeypatch):
    # Covers branch where settings_file is in config_kwargs
    # Mock os.path.exists and file opening/reading so we don't depend on real filesystem files
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("isort.settings._get_config_data", lambda *args, **kwargs: {"line_length": 99})
    
    path = Path("dummy_some_path")
    cfg = _config(path=path, config=DEFAULT_CONFIG, settings_file="dummy_settings.toml")
    # settings_path should not be overwritten by path if settings_file is present
    assert not hasattr(cfg, "settings_path") or cfg.settings_path != path


def test_config_with_kwargs_and_custom_config_raises():
    # Covers lines 651-655: config_kwargs is non-empty and config is not DEFAULT_CONFIG
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=80)


def test_config_with_kwargs_only():
    # Covers lines 651, 658, 660: config_kwargs is non-empty, config is DEFAULT_CONFIG
    cfg = _config(line_length=120)
    assert cfg.line_length == 120


def test_config_default_only():
    # Covers path=None, config=DEFAULT_CONFIG, no kwargs
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
