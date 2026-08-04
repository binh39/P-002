# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 645, 646, 647, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config






def test_config_with_path_and_existing_settings_file(tmp_path: Path):
    # Tests when path is provided, but settings_file is in config_kwargs.
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[isort]\n", encoding="utf-8")
    cfg = _config(path=tmp_path, settings_file=str(settings_file))
    assert cfg is not None


def test_config_with_kwargs_and_custom_config_raises_value_error():
    # Tests that passing both a custom config object and config_kwargs raises ValueError.
    # This hits lines 651-655.
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options"):
        _config(config=custom_config, line_length=120)


def test_config_with_kwargs_only():
    # Tests passing config_kwargs without a custom config object (uses DEFAULT_CONFIG).
    # This hits lines 651, 658, 660.
    cfg = _config(line_length=150)
    assert cfg.line_length == 150
