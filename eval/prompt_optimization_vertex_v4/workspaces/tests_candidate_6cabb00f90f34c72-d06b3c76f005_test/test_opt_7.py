# file: src\sample_repo\isort\isort\settings.py:789-817
# asked: {"lines": [789, 795, 797, 798, 799, 800, 802, 803, 804, 806, 807, 808, 809, 811, 813, 814, 815, 817], "branches": [[797, 798], [797, 817], [798, 797], [798, 799], [800, 798], [800, 801], [813, 798], [813, 814]]}
# gained: {"lines": [789, 795, 797, 798, 799, 800, 802, 803, 804, 806, 807, 808, 809, 811, 813, 817], "branches": [[797, 798], [797, 817], [798, 797], [798, 799], [800, 798], [800, 801], [813, 798]]}

import os
import tempfile
import pytest
from isort.settings import find_all_configs, CONFIG_SOURCES, CONFIG_SECTIONS


def test_find_all_configs_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Pick the first config source available
        config_name = list(CONFIG_SOURCES)[0]
        config_path = os.path.join(tmpdir, config_name)

        # Create a valid config file that _get_config_data can parse successfully
        # For setup.cfg or .editorconfig etc., writing something valid or minimal depending on parser
        # Usually an empty file or basic header works or depends on the specific source.
        # Let's test with valid contents or whatever _get_config_data expects.
        section = CONFIG_SECTIONS.get(config_name)
        
        # Write config file content. If it's setup.cfg, we might need [isort]
        content = ""
        if "setup.cfg" in config_name:
            content = "[isort]\nline_length = 88\n"
        elif "pyproject.toml" in config_name:
            content = "[tool.isort]\nline_length = 88\n"
        elif ".editorconfig" in config_name:
            content = "[*.py]\nisort_line_length = 88\n"
        else:
            content = "line_length = 88\n"

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        trie = find_all_configs(tmpdir)
        assert trie is not None


def test_find_all_configs_exception():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_name = list(CONFIG_SOURCES)[0]
        config_path = os.path.join(tmpdir, config_name)

        # Write invalid content or structure that causes _get_config_data to raise an exception,
        # triggering the except block (lines 806-811).
        # For example, putting invalid TOML in pyproject.toml or invalid INI in setup.cfg.
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("invalid [[[ content \n bad syntax = = =")

        # Should catch exception, warn, set config_data = {}, and not insert into trie (or handle gracefully)
        with pytest.warns(UserWarning, match=f"Failed to pull configuration information from"):
            trie = find_all_configs(tmpdir)

        assert trie is not None
