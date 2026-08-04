# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
import pytest
from isort.settings import Config
from isort.place import _src_path

def test_src_path_none_and_module(tmp_path):
    # Tests:
    # 1. src_paths is None (uses config.src_paths)
    # 2. _is_module(module_path) is True
    mod_file = tmp_path / "mymod.py"
    mod_file.write_text("x = 1")
    
    config = Config(src_paths=[tmp_path])
    res = _src_path("mymod", config, src_paths=None)
    assert res is not None
    section, msg = res
    assert section == "FIRSTPARTY"
    assert f"Found in one of the configured src_paths: {tmp_path.resolve()}" in msg

def test_src_path_prefix_and_module_not_dir_equals_root(tmp_path):
    # Tests:
    # 1. not prefix
    # 2. not module_path.is_dir()
    # 3. src_path.name == root_module_name (so module_path becomes src_path.resolve())
    # 4. _src_path_is_module(src_path, root_module_name) or _is_package
    sub_dir = tmp_path / "myroot"
    sub_dir.mkdir()
    init_file = sub_dir / "__init__.py"
    init_file.write_text("")

    config = Config()
    res = _src_path("myroot", config, src_paths=[sub_dir])
    assert res is not None
    assert res[0] == "FIRSTPARTY"

def test_src_path_nested_namespace_package_explicit(tmp_path):
    # Tests nested_module and namespace in config.namespace_packages
    sub_dir = tmp_path / "pkg"
    sub_dir.mkdir()
    sub_sub = sub_dir / "sub"
    sub_sub.mkdir()
    mod_file = sub_sub / "mod.py"
    mod_file.write_text("")

    config = Config(namespace_packages=["pkg.sub"])
    res = _src_path("pkg.sub.mod", config, src_paths=[tmp_path])
    assert res is not None
    assert res[0] == "FIRSTPARTY"

def test_src_path_nested_auto_identify_namespace_package(tmp_path):
    # Tests nested_module and auto_identify_namespace_packages with namespace package (no __init__.py, contains .py files)
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    sub_dir = pkg_dir / "subpkg"
    sub_dir.mkdir()
    mod_file = sub_dir / "mymod.py"
    mod_file.write_text("")

    config = Config(auto_identify_namespace_packages=True)
    res = _src_path("mypkg.subpkg.mymod", config, src_paths=[tmp_path])
    assert res is not None
    assert res[0] == "FIRSTPARTY"

def test_src_path_not_found(tmp_path):
    # Tests returning None when module is not found anywhere
    config = Config(src_paths=[tmp_path])
    res = _src_path("nonexistent.module", config)
    assert res is None
