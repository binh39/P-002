# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654, 658, 660], "branches": [[644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}

from pathlib import Path
import pytest

from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config


def test_config_default_and_no_path():
    """Test when path is None and config is DEFAULT_CONFIG with no kwargs."""
    res = _config()
    assert res is DEFAULT_CONFIG








def test_config_with_custom_config_and_kwargs():
    """Test ValueError when both custom config object and config_kwargs are provided."""
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_cfg, line_length=120)


def test_config_with_kwargs_only():
    """Test creating a Config object solely from config_kwargs."""
    res = _config(line_length=111)
    assert res.line_length == 111
