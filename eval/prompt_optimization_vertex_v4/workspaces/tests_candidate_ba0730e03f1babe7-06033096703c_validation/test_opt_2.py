# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
import pytest

from isort import sections
from isort.place import _src_path
from isort.settings import Config


def test_src_path_coverage(tmp_path: Path) -> None:
    # Setup directories and files to hit all branches of _src_path:
    # 1. src_paths is None -> uses config.src_paths
    # 2. not prefix and not module_path.is_dir() and src_path.name == root_module_name -> src_path as module_path
    # 3. nested_module and namespace in config.namespace_packages -> recursive call
    # 4. nested_module and config.auto_identify_namespace_packages and _is_namespace_package(...) -> recursive call
    # 5. _is_module(module_path) or _is_package(module_path) or _src_path_is_module(...) -> returns FIRSTPARTY
    # 6. Fallback / return None at the end

    # Create test structure
    # tmp_path/
    #   my_src/ (contains a module.py)
    #   pkg/ (namespace package or normal package)
    #   root_match/ (where src_path.name == root_module_name)

    my_src = tmp_path / "my_src"
    my_src.mkdir()
    
    # Normal module file inside my_src
    mod_file = my_src / "mymod.py"
    mod_file.write_text("# module")

    # Package directory inside my_src
    pkg_dir = my_src / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("# init")
    
    nested_mod = pkg_dir / "sub.py"
    nested_mod.write_text("# sub module")

    # Namespace package directory (no __init__.py)
    ns_dir = my_src / "myns"
    ns_dir.mkdir()
    ns_sub = ns_dir / "sub.py"
    ns_sub.write_text("# ns sub")

    # src_path whose name == root_module_name
    root_name_dir = tmp_path / "root_name_mod"
    root_name_dir.mkdir()
    (root_name_dir / "__init__.py").write_text("# init")

    config = Config(
        src_paths=[my_src, root_name_dir],
        namespace_packages=["explicit_ns"],
        auto_identify_namespace_packages=True,
    )

    # Test 1: src_paths is None (uses config.src_paths)
    res = _src_path("mymod", config, src_paths=None)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

    # Test 2: not prefix and not module_path.is_dir() and src_path.name == root_module_name
    # Here root_module_name is "root_name_mod", which matches root_name_dir.name
    res = _src_path("root_name_mod", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

    # Test 3: nested_module and namespace in config.namespace_packages
    config_ns = Config(
        src_paths=[my_src],
        namespace_packages=["explicit_ns"],
    )
    # Create explicit_ns directory structure
    exp_dir = my_src / "explicit_ns"
    exp_dir.mkdir()
    (exp_dir / "submod.py").write_text("# sub")

    res = _src_path("explicit_ns.submod", config_ns)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

    # Test 4: nested_module and config.auto_identify_namespace_packages and _is_namespace_package(...)
    # myns is a directory without __init__.py, so auto_identify_namespace_packages recognizes it as a namespace package
    res = _src_path("myns.sub", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

    # Test 5: Standard package / module matching
    res = _src_path("mypkg.sub", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

    # Test 6: Returns None when nothing matches
    res = _src_path("nonexistent.module", config)
    assert res is None
