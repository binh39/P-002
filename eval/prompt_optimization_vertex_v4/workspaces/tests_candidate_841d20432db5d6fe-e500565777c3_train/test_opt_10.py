# file: src\sample_repo\isort\isort\deprecated\finders.py:121-165
# asked: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [131, 133], [134, 135], [134, 147], [136, 137], [136, 139], [137, 136], [137, 138], [139, 140], [139, 142], [140, 139], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [148, 158], [150, 151], [150, 153], [151, 150], [151, 152], [153, 154], [153, 158], [154, 153], [154, 155], [159, 160], [159, 163], [163, 0], [163, 164], [164, 163], [164, 165]]}
# gained: {"lines": [121, 122, 125, 126, 127, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 147, 148, 149, 150, 151, 152, 153, 154, 155, 158, 159, 160, 163, 164, 165], "branches": [[131, 132], [134, 135], [136, 137], [136, 139], [137, 138], [139, 140], [139, 142], [140, 141], [142, 143], [142, 147], [143, 142], [143, 144], [148, 149], [150, 151], [150, 153], [151, 152], [153, 154], [153, 158], [154, 155], [159, 160], [163, 0], [163, 164], [164, 163], [164, 165]]}

import os
import sys
import sysconfig
from isort.settings import Config
from isort.deprecated.finders import PathFinder


def test_path_finder_init_comprehensive(tmp_path):
    # Setup temporary directory structures mimicking virtualenv, conda env, etc.
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    
    # Create venv site-packages structures
    venv_lib_site = venv_dir / "lib" / "python3.10" / "site-packages"
    venv_lib_site.mkdir(parents=True)

    venv_nested_site_deep = venv_dir / "lib" / "python3.10" / "site-packages" / "site-packages"
    venv_nested_site_deep.mkdir(parents=True)

    # Create venv src directory with a subdirectory and a file (to test isdir check)
    venv_src = venv_dir / "src"
    venv_src.mkdir()
    sub_src = venv_src / "sub_package"
    sub_src.mkdir()
    some_file = venv_src / "some_file.py"
    some_file.write_text("# file")

    conda_dir = tmp_path / "conda"
    conda_dir.mkdir()
    conda_lib_site = conda_dir / "lib" / "python3.10" / "site-packages"
    conda_lib_site.mkdir(parents=True)
    conda_nested_site = conda_dir / "lib" / "python3.10" / "extras" / "site-packages"
    conda_nested_site.mkdir(parents=True)

    # Clean / modify environment variables during the test
    old_venv = os.environ.get("VIRTUAL_ENV")
    old_conda = os.environ.get("CONDA_PREFIX")

    try:
        os.environ["VIRTUAL_ENV"] = str(venv_dir)
        os.environ["CONDA_PREFIX"] = str(conda_dir)

        config = Config(settings_path=str(tmp_path))
        finder = PathFinder(config, path=str(tmp_path / "root"))

        # Assertions to ensure all branches and loops executed
        assert finder.virtual_env == os.path.realpath(str(venv_dir))
        assert finder.virtual_env_src == f"{finder.virtual_env}{os.sep}src{os.sep}" or finder.virtual_env_src == f"{finder.virtual_env}/src/"
        
        # Paths might be normalized or raw strings, let's normalize comparison
        finder_paths_normalized = {os.path.normcase(os.path.normpath(p)) for p in finder.paths}

        assert os.path.normcase(os.path.normpath(str(venv_lib_site))) in finder_paths_normalized
        assert os.path.normcase(os.path.normpath(str(venv_nested_site_deep))) in finder_paths_normalized
        assert os.path.normcase(os.path.normpath(str(sub_src))) in finder_paths_normalized
        assert os.path.normcase(os.path.normpath(str(some_file))) not in finder_paths_normalized

        assert finder.conda_env == os.path.realpath(str(conda_dir))
        assert os.path.normcase(os.path.normpath(str(conda_lib_site))) in finder_paths_normalized
        assert os.path.normcase(os.path.normpath(str(conda_nested_site))) in finder_paths_normalized

        stdlib = os.path.normcase(sysconfig.get_paths()["stdlib"])
        assert stdlib in finder_paths_normalized

        for p in sys.path[1:]:
            if p:
                assert os.path.normcase(os.path.normpath(p)) in finder_paths_normalized

    finally:
        if old_venv is not None:
            os.environ["VIRTUAL_ENV"] = old_venv
        else:
            os.environ.pop("VIRTUAL_ENV", None)

        if old_conda is not None:
            os.environ["CONDA_PREFIX"] = old_conda
        else:
            os.environ.pop("CONDA_PREFIX", None)


def test_path_finder_config_env_overrides(tmp_path):
    # Test when config.virtual_env and config.conda_env are explicitly passed
    venv_dir = tmp_path / "custom_venv"
    venv_dir.mkdir()
    conda_dir = tmp_path / "custom_conda"
    conda_dir.mkdir()

    config = Config(virtual_env=str(venv_dir), conda_env=str(conda_dir), settings_path=str(tmp_path))
    finder = PathFinder(config, path=str(tmp_path))

    assert finder.virtual_env == os.path.realpath(str(venv_dir))
    assert finder.conda_env == os.path.realpath(str(conda_dir))
