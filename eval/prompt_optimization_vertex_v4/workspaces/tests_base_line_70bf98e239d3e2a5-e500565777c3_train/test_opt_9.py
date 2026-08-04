# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 142], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 158], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.settings import Config
from isort.deprecated.finders import PathFinder


def test_path_finder_init_comprehensive(tmp_path):
    # Setup mock virtual env and conda env directories
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "lib" / "python3.10" / "site-packages").mkdir(parents=True)
    (venv_dir / "lib" / "python3" / "site-packages" / "nested").mkdir(parents=True)
    
    venv_src_dir = venv_dir / "src" / "pkgA"
    venv_src_dir.mkdir(parents=True)
    # A file in src/ to test that only directories are added (os.path.isdir check)
    (venv_dir / "src" / "some_file.txt").write_text("hello")

    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    (conda_dir / "lib" / "python3.10" / "site-packages").mkdir(parents=True)
    (conda_dir / "lib" / "python3" / "site-packages" / "nested").mkdir(parents=True)

    # Configure Config with virtual_env and conda_env
    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir))

    # Temporarily clear environment variables to test config-driven paths exclusively,
    # or ensure they don't interfere unpredictably.
    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")
    os.environ.pop("VIRTUAL_ENV", None)
    os.environ.pop("CONDA_PREFIX", None)

    try:
        finder = PathFinder(config, path=str(tmp_path / "root"))

        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.virtual_env_src == f"{finder.virtual_env}/src/"
        assert finder.conda_env == os.path.realpath(str(conda_dir))

        # Verify paths contain venv and conda directories (using standard os.path.normpath / os.path.abspath)
        expected_venv_sp = os.path.normpath(str(venv_dir / "lib" / "python3.10" / "site-packages"))
        expected_conda_sp = os.path.normpath(str(conda_dir / "lib" / "python3.10" / "site-packages"))
        expected_venv_src = os.path.normpath(str(venv_src_dir))
        not_expected_file = os.path.normpath(str(venv_dir / "src" / "some_file.txt"))

        normalized_paths = [os.path.normpath(p) for p in finder.paths]

        assert expected_venv_sp in normalized_paths
        assert expected_conda_sp in normalized_paths
        assert expected_venv_src in normalized_paths
        assert not_expected_file not in normalized_paths

        # Also test with env vars instead of config
        os.environ["VIRTUAL_ENV"] = str(venv_dir)
        os.environ["CONDA_PREFIX"] = str(conda_dir)
        config_empty = Config()
        finder_env = PathFinder(config_empty, path=str(tmp_path / "root"))
        assert finder_env.virtual_env == os.path.realpath(str(venv_dir))
        assert finder_env.conda_env == os.path.realpath(str(conda_dir))

    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        else:
            os.environ.pop("VIRTUAL_ENV", None)

        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        else:
            os.environ.pop("CONDA_PREFIX", None)
