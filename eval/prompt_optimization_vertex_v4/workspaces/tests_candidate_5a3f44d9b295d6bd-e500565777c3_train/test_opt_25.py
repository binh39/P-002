# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 179, 180, 182, 183, 184, 186], "branches": [[168, 169], [180, 181], [181, 186]]}

import importlib.machinery
import os
import sys
from pathlib import Path
import pytest

from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_virtual_env_src(tmp_path):
    venv_dir = tmp_path / "my_venv"
    venv_src = venv_dir / "src" / "my_venv_src_pkg"
    venv_src.mkdir(parents=True)
    (venv_src / "py.typed").touch()
    (venv_src.parent / "my_venv_src_pkg.py").write_text("x = 1")

    config = Config()
    finder = PathFinder(config, path=str(tmp_path))
    finder.virtual_env = str(venv_dir)
    finder.virtual_env_src = str(venv_dir / "src")
    finder.paths = [str(venv_src.parent)]

    assert finder.find("my_venv_src_pkg") == sections.THIRDPARTY
