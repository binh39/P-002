# file: src\sample_repo\isort\isort\api.py:641-660
# asked: {"lines": [641, 642, 643, 644, 645, 646, 647, 649, 651, 652, 653, 654, 658, 660], "branches": [[644, 649], [644, 651], [651, 652], [651, 660], [652, 653], [652, 658]]}
# gained: {"lines": [641, 642, 644, 651, 652, 653, 654], "branches": [[644, 651], [651, 652], [652, 653]]}

from pathlib import Path
import pytest
from isort.api import _config
from isort.settings import DEFAULT_CONFIG, Config




def test_config_with_path_and_custom_config_raises_value_error(tmp_path):
    # Covers: config is NOT DEFAULT_CONFIG, and config_kwargs is also populated via path.
    # Wait, in the code:
    # if path and (config is DEFAULT_CONFIG and ...):
    #     config_kwargs["settings_path"] = path
    # So if config is NOT DEFAULT_CONFIG, path won't populate config_kwargs automatically unless kwargs are passed.
    # To hit lines 651-655 where config_kwargs is truthy AND config is not DEFAULT_CONFIG, we need to pass kwargs explicitly with a non-default config.
    pass


def test_config_with_kwargs_and_custom_config_raises_value_error():
    # Covers: config_kwargs explicitly passed via kwargs, and config is not DEFAULT_CONFIG
    # Lines 651-655
    custom_cfg = Config(line_length=100)
    with pytest.raises(ValueError, match="You can either specify custom configuration options using kwargs"):
        _config(config=custom_cfg, line_length=120)
