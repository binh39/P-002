# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.deprecated.finders import PathFinder
from isort.settings import Config


def test_path_finder_init_full_coverage(monkeypatch):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = tmpdir

        venv_dir = os.path.join(tmp_path, "venv")
        os.makedirs(venv_dir, exist_ok=True)
        
        # Match glob pattern: lib/python*/site-packages
        lib_py_site = os.path.join(venv_dir, "lib", "python3.10", "site-packages")
        os.makedirs(lib_py_site, exist_ok=True)

        # Match glob pattern: lib/python*/*/site-packages -> e.g., lib/python3.10/site-packages is python*, wait:
        # python*/*/site-packages means pythonX.Y/something/site-packages
        nested_dir = os.path.join(venv_dir, "lib", "python3.10", "extras", "site-packages")
        os.makedirs(nested_dir, exist_ok=True)

        venv_src_sub = os.path.join(venv_dir, "src", "pkgA")
        os.makedirs(venv_src_sub, exist_ok=True)

        conda_dir = os.path.join(tmp_path, "conda")
        os.makedirs(conda_dir, exist_ok=True)
        conda_lib_py_site = os.path.join(conda_dir, "lib", "python3.10", "site-packages")
        os.makedirs(conda_lib_py_site, exist_ok=True)
        conda_nested_dir = os.path.join(conda_dir, "lib", "python3.10", "extras", "site-packages")
        os.makedirs(conda_nested_dir, exist_ok=True)

        config = Config(virtual_env=venv_dir, conda_env=conda_dir)

        monkeypatch.delenv("VIRTUAL_ENV", raising=False)
        monkeypatch.delenv("CONDA_PREFIX", raising=False)

        finder = PathFinder(config, path=os.path.join(tmp_path, "root"))

        assert os.path.normpath(lib_py_site) in [os.path.normpath(p) for p in finder.paths]
        assert os.path.normpath(nested_dir) in [os.path.normpath(p) for p in finder.paths]
        assert os.path.normpath(venv_src_sub) in [os.path.normpath(p) for p in finder.paths]
        assert os.path.normpath(conda_lib_py_site) in [os.path.normpath(p) for p in finder.paths]
        assert os.path.normpath(conda_nested_dir) in [os.path.normpath(p) for p in finder.paths]
        assert finder.stdlib_lib_prefix in finder.paths
        for sp in sys.path[1:]:
            if sp:
                assert sp in finder.paths


def test_path_finder_env_vars_and_duplicates(monkeypatch):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_dir = os.path.join(tmpdir, "venv_env")
        os.makedirs(venv_dir, exist_ok=True)
        os.makedirs(os.path.join(venv_dir, "src"), exist_ok=True)

        monkeypatch.setenv("VIRTUAL_ENV", venv_dir)
        monkeypatch.setenv("CONDA_PREFIX", venv_dir)

        config = Config()

        stdlib = os.path.normcase(sysconfig.get_paths()["stdlib"])
        
        finder = PathFinder(config, path=tmpdir)
        assert finder.virtual_env == os.path.realpath(venv_dir)
        assert finder.conda_env == os.path.realpath(venv_dir)
        assert stdlib in finder.paths
