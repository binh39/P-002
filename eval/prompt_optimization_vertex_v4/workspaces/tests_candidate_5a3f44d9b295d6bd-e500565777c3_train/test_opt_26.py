# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config






def test_config_with_custom_config_and_kwargs():
    # Covers lines 652-655 (ValueError when both config and config_kwargs are provided)
    custom_config = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_config, line_length=80)


def test_config_with_only_kwargs():
    # Covers config_kwargs present, config is DEFAULT_CONFIG, no path
    cfg = _config(line_length=120)
    assert cfg.line_length == 120


def test_config_with_default_config_no_kwargs():
    # Covers when config_kwargs is empty and path is None (returning DEFAULT_CONFIG directly)
    cfg = _config(path=None, config=DEFAULT_CONFIG)
    assert cfg is DEFAULT_CONFIG
