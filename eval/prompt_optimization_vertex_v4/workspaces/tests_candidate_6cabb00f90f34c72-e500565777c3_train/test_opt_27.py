# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_path_default_config_no_settings_kwargs(tmp_path: Path):
    # Exercises:
    # - path is truthy
    # - config is DEFAULT_CONFIG
    # - "settings_path" not in config_kwargs
    # - "settings_file" not in config_kwargs
    # - config_kwargs becomes truthy (adds settings_path)
    # - config is not not DEFAULT_CONFIG (config is DEFAULT_CONFIG) -> skips ValueError
    # - config = Config(**config_kwargs) executed
    cfg = _config(path=tmp_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_with_custom_config_and_kwargs(tmp_path: Path):
    # Exercises:
    # - config_kwargs is truthy
    # - config is NOT DEFAULT_CONFIG
    # -> raises ValueError
    custom_config = Config(settings_path=tmp_path)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=100)


def test_config_no_path_no_kwargs():
    # Exercises:
    # - path is None (falsy)
    # - config_kwargs is empty (falsy)
    # Returns DEFAULT_CONFIG directly without modification
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
