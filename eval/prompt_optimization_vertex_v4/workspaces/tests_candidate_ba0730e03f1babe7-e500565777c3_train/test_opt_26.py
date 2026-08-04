# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 179, 180, 182, 183, 184, 187, 189, 191, 192, 195, 198], "branches": [[168, 169], [180, 181], [181, 187], [187, 189], [189, 191], [191, 192], [191, 195], [192, 191], [195, 198]]}

import os
from pathlib import Path
from isort import sections
from isort.deprecated.finders import PathFinder
from isort.settings import Config




def test_path_finder_virtual_env_src(tmp_path):
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    venv_src = venv_dir / "src" / "pkg"
    venv_src.mkdir(parents=True)
    mod_venv = venv_src / "mod_venv.py"
    mod_venv.write_text("x = 1")

    config = Config()
    finder = PathFinder(config)
    finder.virtual_env = str(venv_dir.resolve())
    finder.virtual_env_src = str((venv_dir / "src").resolve()) + "/"
    finder.paths = [str(venv_src.resolve())]

    assert finder.find("mod_venv") == sections.THIRDPARTY
