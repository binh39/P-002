# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

import tempfile
from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_no_args():
    # Covers: path=None, config=DEFAULT_CONFIG, no config_kwargs
    # Branches: path is falsy, config_kwargs is empty -> returns DEFAULT_CONFIG
    cfg = _config()
    assert cfg is DEFAULT_CONFIG






def test_config_with_path_and_existing_settings_file_kwarg():
    # Covers line 644 where "settings_file" is already in config_kwargs
    # Branches: path is truthy, but "settings_file" in config_kwargs is True
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        toml_file = base / "pyproject.toml"
        toml_file.write_text("[tool.isort]\nline_length = 79")
        p = base / "fallback"
        p.mkdir()
        cfg = _config(path=p, settings_file=str(toml_file))
        assert cfg.line_length == 79


def test_config_with_kwargs_only():
    # Covers lines 651, 658, 660
    # Branches: config_kwargs is truthy, config is DEFAULT_CONFIG -> creates new Config with kwargs
    cfg = _config(line_length=100)
    assert isinstance(cfg, Config)
    assert cfg.line_length == 100


def test_config_raises_value_error_when_config_and_kwargs_provided():
    # Covers lines 651-655
    # Branches: config_kwargs is truthy, config is NOT DEFAULT_CONFIG -> raises ValueError
    custom_config = Config(line_length=88)
    with pytest.raises(
        ValueError,
        match="You can either specify custom configuration options using kwargs or passing in a Config object. Not Both!",
    ):
        _config(config=custom_config, line_length=100)
