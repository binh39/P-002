# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config






def test_config_with_custom_config_and_kwargs(tmp_path: Path) -> None:
    # Covers: config_kwargs is truthy AND config is not DEFAULT_CONFIG -> raises ValueError
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=80)


def test_config_with_only_custom_config() -> None:
    # Covers: config_kwargs is empty, config is not DEFAULT_CONFIG
    custom_config = Config(line_length=120)
    cfg = _config(config=custom_config)
    assert cfg is custom_config
    assert cfg.line_length == 120


def test_config_default_no_args() -> None:
    # Covers: path is None, config is DEFAULT_CONFIG, config_kwargs is empty
    cfg = _config()
    assert cfg is DEFAULT_CONFIG
