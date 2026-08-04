# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.settings import Config
from isort.deprecated.finders import PathFinder




def test_path_finder_env_fallbacks_and_duplicates(tmp_path, monkeypatch):
    venv_dir = tmp_path / "venv2"
    venv_dir.mkdir()
    venv_site = venv_dir / "lib" / "python3.10" / "site-packages"
    venv_site.mkdir(parents=True)

    monkeypatch.setenv("VIRTUAL_ENV", str(venv_dir))
    monkeypatch.setenv("CONDA_PREFIX", "")

    config = Config(settings_path=tmp_path)
    
    finder = PathFinder(config=config, path=str(tmp_path))
    assert finder.virtual_env == os.path.realpath(venv_dir)
    assert finder.conda_env == ""
