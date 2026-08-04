# file: src\sample_repo\isort\isort\settings.py:789-817
# asked: {"lines": [789, 795, 797, 798, 799, 800, 802, 803, 804, 806, 807, 808, 809, 811, 813, 814, 815, 817], "branches": [[797, 798], [797, 817], [798, 797], [798, 799], [800, 798], [800, 801], [813, 798], [813, 814]]}
# gained: {"lines": [789, 795, 797, 798, 799, 800, 802, 803, 804, 806, 807, 808, 809, 811, 813, 814, 815, 817], "branches": [[797, 798], [797, 817], [798, 797], [798, 799], [800, 798], [800, 801], [813, 798], [813, 814]]}

import os
import tempfile
import pytest
from isort.settings import find_all_configs, CONFIG_SOURCES


def test_find_all_configs_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_name = CONFIG_SOURCES[0]
        config_file = os.path.join(tmpdir, config_name)
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("[isort]\nprofile = \"black\"\n")

        trie = find_all_configs(tmpdir)
        assert trie is not None


def test_find_all_configs_exception(monkeypatch):
    import isort.settings as settings

    with tempfile.TemporaryDirectory() as tmpdir:
        config_name = CONFIG_SOURCES[0]
        config_file = os.path.join(tmpdir, config_name)
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("invalid content that causes exception")

        def mock_get_config_data(*args, **kwargs):
            raise ValueError("Simulated parsing error")

        monkeypatch.setattr(settings, "_get_config_data", mock_get_config_data)

        with pytest.warns(UserWarning, match="Failed to pull configuration information from"):
            trie = find_all_configs(tmpdir)

        assert trie is not None
