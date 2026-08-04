# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

import pytest
from pathlib import Path
from isort import sections
from isort.settings import Config
from isort.place import _src_path

def test_src_path_coverage(tmp_path: Path):
    # Setup directories and files for testing _src_path branches
    
    # 1. src_path.name == root_module_name branch (lines 79-80)
    # When not prefix, module_path is not a dir, and src_path.name == root_module_name
    src1 = tmp_path / "mypkg"
    src1.mkdir()
    # Create a file inside src1 so it acts as a module or package, or test _src_path_is_module
    # Let's create a file mypkg.py inside parent or test _src_path_is_module
    # Wait, if module_path = src1 / root_module_name -> src1 / "mypkg", which is not a dir.
    # But src1.name == root_module_name ("mypkg"). So module_path becomes src1.resolve().
    config1 = Config(src_paths=[src1])
    
    # Let's also create a module file so _is_module(module_path) returns True
    # If module_path becomes src1.resolve(), we need src1 to be a module file or have a module file.
    # Wait, _is_module checks if module_path + extension is a file.
    # Let's create `mypkg.py` inside `tmp_path`.
    mod_file = tmp_path / "mypkg.py"
    mod_file.write_text("print('hello')")
    
    # Let's test calling _src_path with name="mypkg" and src_paths=[src1] where src1.name == "mypkg" and not src1/mypkg.is_dir().
    # module_path becomes (src1 / "mypkg").resolve() -> tmp_path / "mypkg". Not a dir.
    # since not prefix and not module_path.is_dir() and src_path.name == root_module_name:
    # module_path = src1.resolve() -> tmp_path / "mypkg" (which is src1, a directory? Wait, src1 is a directory).
    # If module_path is a directory, _is_package(module_path) will be True!
    res1 = _src_path("mypkg", config1, src_paths=[src1])
    assert res1 is not None
    assert res1[0] == sections.FIRSTPARTY

    # 2. nested_module and namespace_packages / auto_identify_namespace_packages (lines 81-88)
    sub_src = tmp_path / "namespace_pkg"
    sub_src.mkdir()
    sub_child = sub_src / "child"
    sub_child.mkdir()
    
    config_ns = Config(
        src_paths=[sub_src],
        namespace_packages=["namespace_pkg"],
        auto_identify_namespace_packages=True,
    )
    res_ns = _src_path("namespace_pkg.child.foo", config_ns)
    # Since namespace_pkg is in namespace_packages, it should recurse into nested_module
    # Eventually returns None if foo doesn't exist, but exercises lines 81-88.
    
    # Also test auto_identify_namespace_packages branch with a namespace package
    config_auto_ns = Config(
        src_paths=[sub_src],
        auto_identify_namespace_packages=True,
    )
    # A namespace package has no __init__.py
    res_auto_ns = _src_path("namespace_pkg.child.bar", config_auto_ns)

    # 3. _src_path_is_module or standard module/package match (lines 89-94)
    pkg_path = tmp_path / "regular_pkg"
    pkg_path.mkdir()
    (pkg_path / "__init__.py").write_text("")
    config_reg = Config(src_paths=[pkg_path])
    res_reg = _src_path("regular_pkg", config_reg)
    assert res_reg is not None

    # 4. Fallback / return None (line 96)
    res_none = _src_path("nonexistent_module_xyz", config_reg)
    assert res_none is None
