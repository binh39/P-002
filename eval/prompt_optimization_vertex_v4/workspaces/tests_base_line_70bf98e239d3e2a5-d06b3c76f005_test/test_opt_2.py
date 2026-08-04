# file: src\sample_repo\isort\isort\settings.py:789-817
# asked: {"lines": [789, 795, 797, 798, 799, 800, 802, 803, 804, 806, 807, 808, 809, 811, 813, 814, 815, 817], "branches": [[797, 798], [797, 817], [798, 797], [798, 799], [800, 798], [800, 801], [813, 798], [813, 814]]}
# gained: {"lines": [789, 795, 797, 798, 799, 800, 802, 803, 804, 806, 807, 808, 809, 811, 813, 814, 815, 817], "branches": [[797, 798], [797, 817], [798, 797], [798, 799], [800, 798], [800, 801], [813, 798], [813, 814]]}

import os
import pytest
from isort.settings import find_all_configs, CONFIG_SOURCES


def test_find_all_configs(tmp_path):
    # Create a valid config file
    config_name = list(CONFIG_SOURCES)[0]
    config_file = tmp_path / config_name
    config_file.write_text("invalid_toml_or_ini_content = [unclosed")

    # Also test successful config parsing or subdirectories if needed,
    # but specifically this will trigger os.path.isfile -> exception -> warn -> config_data = {}
    # and if we create an empty config or valid one, test the success path / break as well.
    
    # Let's test with a valid config file in a subdirectory
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    valid_config_file = sub_dir / config_name
    # Writing something that parses successfully or triggers exception depending on CONFIG_SECTIONS
    # A simple valid section or key-value depending on the config type (.isort.cfg / setup.cfg etc.)
    if config_name == ".isort.cfg":
        valid_config_file.write_text("[isort]\nprofile = black\n")
    elif config_name == "pyproject.toml":
        valid_config_file.write_text("[tool.isort]\nprofile = \"black\"\n")
    else:
        valid_config_file.write_text("[isort]\nprofile = black\n")

    trie = find_all_configs(str(tmp_path))
    assert trie is not None
