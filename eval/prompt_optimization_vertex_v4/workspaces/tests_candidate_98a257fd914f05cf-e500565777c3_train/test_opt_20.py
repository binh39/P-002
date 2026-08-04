# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 139, 142, 147, 148, 149, 150, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 139], [139, 142], [142, 147], [148, 149], [150, 153], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.settings import Config
from isort.deprecated.finders import PathFinder




def test_path_finder_env_fallbacks(tmp_path):
    # Test when virtual_env and conda_env are picked up from os.environ
    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")

    venv_dir = tmp_path / "env_venv"
    venv_dir.mkdir()
    conda_dir = tmp_path / "env_conda"
    conda_dir.mkdir()

    os.environ["VIRTUAL_ENV"] = str(venv_dir)
    os.environ["CONDA_PREFIX"] = str(conda_dir)

    try:
        config = Config()  # no virtual_env or conda_env in config
        finder = PathFinder(config, path=str(tmp_path))
        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.conda_env == os.path.realpath(str(conda_dir))
    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        else:
            os.environ.pop("VIRTUAL_ENV", None)

        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        else:
            os.environ.pop("CONDA_PREFIX", None)
