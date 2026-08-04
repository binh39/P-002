# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_with_path_and_default_config(tmp_path: Path) -> None:
    # Covers: path is truthy, config is DEFAULT_CONFIG, and neither settings_path nor settings_file in config_kwargs (lines 644-649)
    # Also covers config_kwargs is truthy, config is DEFAULT_CONFIG, returning Config (lines 651-660)
    cfg = _config(path=tmp_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_with_path_and_existing_settings_path(tmp_path: Path) -> None:
    # Covers: path is truthy, but "settings_path" is already in config_kwargs -> should not override settings_path with path
    custom_path = tmp_path / "subdir"
    custom_path.mkdir()
    cfg = _config(path=tmp_path, settings_path=custom_path)
    assert cfg is not DEFAULT_CONFIG


def test_config_with_path_and_existing_settings_file(tmp_path: Path) -> None:
    # Covers: path is truthy, but "settings_file" is in config_kwargs -> should not override with settings_path
    settings_file = tmp_path / ".pyproject.toml"
    settings_file.write_text("[tool.isort]\n")
    cfg = _config(path=tmp_path, settings_file=str(settings_file))
    assert cfg is not DEFAULT_CONFIG


def test_config_with_custom_config_and_kwargs(tmp_path: Path) -> None:
    # Covers: config_kwargs is truthy, but config is NOT DEFAULT_CONFIG -> raises ValueError (lines 651-655)
    custom_config = Config(settings_path=str(tmp_path))
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, profile="black")


def test_config_no_path_no_kwargs() -> None:
    # Covers: path is None/falsy, config_kwargs is empty -> returns config as-is
    cfg = _config(config=DEFAULT_CONFIG)
    assert cfg is DEFAULT_CONFIG
