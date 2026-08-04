# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default_and_no_kwargs():
    res = _config()
    assert res is DEFAULT_CONFIG


def test_config_with_path_and_default_config(tmp_path):
    res = _config(path=tmp_path)
    assert isinstance(res, Config)


def test_config_with_path_but_settings_path_in_kwargs(tmp_path):
    p1 = tmp_path / "p1"
    p1.mkdir()
    p2 = tmp_path / "p2"
    p2.mkdir()
    res = _config(path=p1, settings_path=str(p2))
    assert isinstance(res, Config)


def test_config_with_path_but_settings_file_in_kwargs(tmp_path):
    settings_file = tmp_path / "pyproject.toml"
    settings_file.write_text("[tool.isort]\nline_length = 88")
    res = _config(path=tmp_path, settings_file=str(settings_file))
    assert isinstance(res, Config)


def test_config_with_custom_config_and_kwargs_raises_value_error():
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_cfg, line_length=120)


def test_config_with_custom_config_only():
    custom_cfg = Config(line_length=100)
    res = _config(config=custom_cfg)
    assert res is custom_cfg


def test_config_with_kwargs_only():
    res = _config(line_length=111)
    assert isinstance(res, Config)
    assert res.line_length == 111
