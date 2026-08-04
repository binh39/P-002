# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_with_path_and_default_config(tmp_path: Path) -> None:
    cfg = _config(path=tmp_path)
    assert isinstance(cfg, Config)


def test_config_with_path_and_existing_settings_path_kwarg(tmp_path: Path) -> None:
    other_path = tmp_path / "other"
    other_path.mkdir()
    # settings_path is already in config_kwargs, so path shouldn't override it
    cfg = _config(path=tmp_path, settings_path=other_path)
    assert isinstance(cfg, Config)


def test_config_with_path_and_existing_settings_file_kwarg(tmp_path: Path) -> None:
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\nline_length = 88")
    
    # settings_file is in config_kwargs, so path shouldn't override it
    cfg = _config(path=tmp_path, settings_file=str(settings_file))
    assert cfg.line_length == 88


def test_config_with_custom_config_and_config_kwargs() -> None:
    custom_config = Config(line_length=88)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=79)


def test_config_with_only_config_kwargs() -> None:
    cfg = _config(line_length=100)
    assert cfg.line_length == 100


def test_config_with_default_config_and_no_kwargs() -> None:
    cfg = _config(path=None, config=DEFAULT_CONFIG)
    assert cfg is DEFAULT_CONFIG
