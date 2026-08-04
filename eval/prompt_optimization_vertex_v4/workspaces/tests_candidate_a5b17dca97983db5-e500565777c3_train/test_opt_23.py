# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 147], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_env_fallback(tmp_path):
    # Test fallback to os.environ when config values are empty/None
    env_venv = tmp_path / "env_venv"
    env_venv.mkdir()
    (env_venv / "lib" / "python3.8" / "site-packages").mkdir(parents=True)

    env_conda = tmp_path / "env_conda"
    env_conda.mkdir()
    (env_conda / "lib" / "python3.8" / "site-packages").mkdir(parents=True)

    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")

    os.environ["VIRTUAL_ENV"] = str(env_venv)
    os.environ["CONDA_PREFIX"] = str(env_conda)

    try:
        config = Config(settings_path=tmp_path)
        finder = PathFinder(config, path=str(tmp_path))

        assert finder.virtual_env == os.path.realpath(str(env_venv))
        assert finder.conda_env == os.path.realpath(str(env_conda))
        
        real_paths = [os.path.realpath(p) for p in finder.paths]
        assert os.path.realpath(str(env_venv / "lib" / "python3.8" / "site-packages")) in real_paths
        assert os.path.realpath(str(env_conda / "lib" / "python3.8" / "site-packages")) in real_paths
    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        else:
            os.environ.pop("VIRTUAL_ENV", None)

        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        else:
            os.environ.pop("CONDA_PREFIX", None)
