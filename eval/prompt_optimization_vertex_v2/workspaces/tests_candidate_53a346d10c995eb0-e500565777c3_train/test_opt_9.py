# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 139, 142, 147, 148, 149, 150, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 139], [139, 142], [142, 147], [148, 149], [150, 153], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
import tempfile
import pytest
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_env_vars_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = tmpdir
        venv_dir = os.path.join(tmp_path, "env_venv")
        os.mkdir(venv_dir)
        conda_dir = os.path.join(tmp_path, "env_conda")
        os.mkdir(conda_dir)

        old_venv = os.environ.get("VIRTUAL_ENV")
        old_conda = os.environ.get("CONDA_PREFIX")

        os.environ["VIRTUAL_ENV"] = venv_dir
        os.environ["CONDA_PREFIX"] = conda_dir

        try:
            config = Config()
            finder = PathFinder(config, path=tmp_path)
            assert finder.virtual_env == os.path.realpath(venv_dir)
            assert finder.conda_env == os.path.realpath(conda_dir)
        finally:
            if old_venv is not None:
                os.environ["VIRTUAL_ENV"] = old_venv
            elif "VIRTUAL_ENV" in os.environ:
                del os.environ["VIRTUAL_ENV"]

            if old_conda is not None:
                os.environ["CONDA_PREFIX"] = old_conda
            elif "CONDA_PREFIX" in os.environ:
                del os.environ["CONDA_PREFIX"]
