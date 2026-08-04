# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_with_path_and_default_config(tmp_path: Path) -> None:
    # Covers: path is truthy, config is DEFAULT_CONFIG, and neither settings_path nor settings_file in config_kwargs.
    # Also covers: config_kwargs is truthy, config is DEFAULT_CONFIG -> creates new Config with settings_path = path.
    cfg = _config(path=tmp_path)
    assert isinstance(cfg, Config)
    # When settings_path is passed via path, isort finds config or sets directory accordingly.
    # Let's check that it successfully instantiated a Config object with the given path as settings_path or source/directory.
    assert cfg is not DEFAULT_CONFIG


def test_config_with_path_and_settings_path_in_kwargs(tmp_path: Path) -> None:
    # Covers: path is truthy, but settings_path is already in config_kwargs (so path doesn't get added to config_kwargs)
    other_path = tmp_path / "sub"
    other_path.mkdir()
    cfg = _config(path=tmp_path, settings_path=other_path)
    assert isinstance(cfg, Config)
    assert cfg is not DEFAULT_CONFIG


def test_config_with_custom_config_and_config_kwargs(tmp_path: Path) -> None:
    # Covers: config_kwargs is truthy, but config is NOT DEFAULT_CONFIG -> raises ValueError
    custom_config = Config(settings_path=str(tmp_path))
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, profile="black")


def test_config_no_kwargs_custom_config(tmp_path: Path) -> None:
    # Covers: config_kwargs is empty, config is not DEFAULT_CONFIG -> returns config as is
    custom_config = Config(settings_path=str(tmp_path))
    cfg = _config(config=custom_config)
    assert cfg is custom_config


def test_config_no_kwargs_default_config() -> None:
    # Covers: config_kwargs is empty, config is DEFAULT_CONFIG -> returns DEFAULT_CONFIG
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
