# file: src\sample_repo\isort\isort\deprecated\finders.py:167-199
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175, 177, 179, 180, 182, 183, 184, 186, 187, 188, 189, 190, 191, 192, 193, 195, 196, 198, 199], "branches": [[168, 169], [168, 199], [180, 168], [180, 181], [181, 186], [181, 187], [187, 188], [187, 189], [189, 190], [189, 191], [191, 192], [191, 195], [192, 191], [192, 193], [195, 196], [195, 198]]}

from pathlib import Path
import tempfile
import os

from isort.deprecated.finders import PathFinder
from isort.settings import Config
from isort import sections


def test_path_finder_find_all_branches():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        
        # Create directories and files to test various conditions:
        # 1. site-packages / dist-packages prefix -> THIRDPARTY
        site_pkg_dir = tmp_path / "site-packages"
        site_pkg_dir.mkdir()
        (site_pkg_dir / "mod_site.py").write_text("# mod")
        
        # 2. stdlib_lib_prefix -> STDLIB
        # We can simulate or use config / subclass or adjust PathFinder.paths
        # Let's inspect how stdlib_lib_prefix is set. It is os.path.normcase(sysconfig.get_paths()['stdlib']).
        # If we put a module in stdlib or add a prefix matching stdlib_lib_prefix:
        # Wait, line 187: os.path.normcase(prefix) == self.stdlib_lib_prefix
        
        # 3. conda_env -> THIRDPARTY
        conda_dir = tmp_path / "conda_env"
        conda_dir.mkdir()
        (conda_dir / "mod_conda.py").write_text("# mod")

        # 4. src_paths -> FIRSTPARTY (and not skipped)
        src_dir = tmp_path / "src_root"
        src_dir.mkdir()
        sub_src = src_dir / "mypkg"
        sub_src.mkdir()
        (sub_src / "__init__.py").write_text("# pkg")

        # 5. stdlib_lib_prefix starts with -> STDLIB (line 195)
        # 6. default_section (line 198)
        default_dir = tmp_path / "other_prefix"
        default_dir.mkdir()
        (default_dir / "mod_default.py").write_text("# mod")

        # 7. Returns None if not found (line 199)

        config = Config(src_paths=[str(src_dir)])

        finder = PathFinder(config, path=str(tmp_path))
        
        # Test site-packages -> THIRDPARTY
        finder.paths = [str(site_pkg_dir)]
        assert finder.find("mod_site") == sections.THIRDPARTY

        # Test dist-packages -> THIRDPARTY
        dist_pkg_dir = tmp_path / "dist-packages"
        dist_pkg_dir.mkdir()
        (dist_pkg_dir / "mod_dist.py").write_text("# mod")
        finder.paths = [str(dist_pkg_dir)]
        assert finder.find("mod_dist") == sections.THIRDPARTY

        # Test virtual_env and virtual_env_src -> THIRDPARTY
        finder.virtual_env = str(tmp_path / "venv")
        finder.virtual_env_src = str(tmp_path / "venv" / "src")
        venv_src_mod = tmp_path / "venv" / "src" / "my_venv_mod"
        venv_src_mod.mkdir(parents=True)
        (venv_src_mod / "__init__.py").write_text("")
        finder.paths = [str(venv_src_mod.parent)]
        assert finder.find("my_venv_mod") == sections.THIRDPARTY

        # Test stdlib_lib_prefix == normcase(prefix) -> STDLIB
        finder.virtual_env = None
        finder.conda_env = None
        finder.stdlib_lib_prefix = os.path.normcase(str(tmp_path / "stdlib"))
        stdlib_dir = tmp_path / "stdlib"
        stdlib_dir.mkdir(exist_ok=True)
        (stdlib_dir / "mod_stdlib.py").write_text("")
        finder.paths = [str(stdlib_dir)]
        assert finder.find("mod_stdlib") == sections.STDLIB

        # Test conda_env and conda_env in prefix -> THIRDPARTY
        finder.stdlib_lib_prefix = "nonexistent_stdlib"
        finder.conda_env = str(tmp_path / "conda")
        conda_prefix_dir = tmp_path / "conda" / "envs" / "myenv"
        conda_prefix_dir.mkdir(parents=True)
        (conda_prefix_dir / "mod_conda_env.py").write_text("")
        finder.paths = [str(conda_prefix_dir)]
        assert finder.find("mod_conda_env") == sections.THIRDPARTY

        # Test src_paths in path_obj.parents and not skipped -> FIRSTPARTY
        finder.conda_env = None
        finder.paths = [str(src_dir)]
        assert finder.find("mypkg") == sections.FIRSTPARTY

        # Test stdlib_lib_prefix.startswith -> STDLIB (line 195)
        # prefix starts with stdlib_lib_prefix
        parent_stdlib = tmp_path / "parent_stdlib"
        parent_stdlib.mkdir(exist_ok=True)
        finder.stdlib_lib_prefix = os.path.normcase(str(parent_stdlib))
        sub_stdlib = parent_stdlib / "sub"
        sub_stdlib.mkdir(exist_ok=True)
        (sub_stdlib / "mod_sub_stdlib.py").write_text("")
        finder.paths = [str(sub_stdlib)]
        assert finder.find("mod_sub_stdlib") == sections.STDLIB

        # Test default section -> default_section (line 198)
        finder.stdlib_lib_pin = "nonexistent"
        finder.stdlib_lib_prefix = "nonexistent"
        finder.config = Config(default_section="CUSTOMSECTION", src_paths=[])
        other_dir = tmp_path / "other"
        other_dir.mkdir(exist_ok=True)
        (other_dir / "mod_other.py").write_text("")
        finder.paths = [str(other_dir)]
        assert finder.find("mod_other") == "CUSTOMSECTION"

        # Test returns None (line 199)
        finder.paths = [str(other_dir)]
        assert finder.find("nonexistent_module") is None


def test_path_finder_extension_suffixes():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        ext_dir = tmp_path / "ext_pkg"
        ext_dir.mkdir()
        
        # Create a dummy file with an extension suffix from importlib.machinery.EXTENSION_SUFFIXES
        import importlib.machinery
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
        (ext_dir / f"mymodule{suffix}").write_text("")

        config = Config(src_paths=[])
        finder = PathFinder(config, path=str(tmp_path))
        finder.paths = [str(ext_dir)]
        finder.stdlib_lib_prefix = "none"
        
        assert finder.find("mymodule") == finder.config.default_section
