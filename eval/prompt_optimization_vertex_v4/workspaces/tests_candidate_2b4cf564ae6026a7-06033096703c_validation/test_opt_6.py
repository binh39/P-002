# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 94]]}

from pathlib import Path
import pytest
from isort.place import _src_path
from isort.settings import Config
from isort import sections

def test_src_path_default_src_paths_and_not_found(tmp_path):
    config = Config(src_paths=[])
    assert _src_path("foo", config) is None

def test_src_path_prefix_handling_and_src_path_name(tmp_path):
    # Tests:
    # 1. src_paths is None -> uses config.src_paths
    # 2. not prefix and not module_path.is_dir() and src_path.name == root_module_name -> module_path = src_path.resolve()
    # 3. _is_module(module_path) branch returning FIRSTPARTY
    sub = tmp_path / "foo"
    sub.mkdir()
    py_file = tmp_path / "foo.py"
    py_file.write_text("x = 1")

    config = Config(src_paths=(sub,))
    # Here src_path is `sub` (name "foo"), root_module_name is "foo".
    # module_path becomes (sub / "foo") which is not a dir.
    # src_path.name == root_module_name is True -> module_path becomes sub.resolve().
    # Then `_is_module(sub)` checks for sub.with_suffix('.py') etc.
    # Wait, `sub.with_suffix('.py')` would be `tmp_path / "foo.py"`, but module_path is `sub`.
    # Let's make sure we hit a condition where _is_module or _is_package or _src_path_is_module is True.
    # If src_path is tmp_path / "foo", and root_module_name is "foo", module_path = tmp_path / "foo" / "foo".
    # Not dir, but src_path.name == root_module_name ("foo" == "foo") -> module_path becomes tmp_path / "foo" (which is a dir, so _is_package is True).
    res = _src_path("foo", config)
    assert res == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {sub}.")

def test_src_path_nested_module_and_namespace_packages(tmp_path):
    # Tests:
    # 1. nested_module and namespace in config.namespace_packages
    sub = tmp_path / "pkg"
    sub.mkdir()
    
    nested_sub = sub / "sub"
    nested_sub.mkdir()
    (nested_sub / "__init__.py").write_text("")

    config = Config(
        src_paths=(tmp_path,),
        namespace_packages=("pkg",)
    )
    res = _src_path("pkg.sub", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

def test_src_path_auto_identify_namespace_packages(tmp_path):
    # Tests:
    # 1. nested_module and config.auto_identify_namespace_packages and _is_namespace_package(module_path, ...)
    sub = tmp_path / "ns"
    sub.mkdir()
    
    nested_sub = sub / "sub"
    nested_sub.mkdir()
    # Namespace package without __init__.py or with pkgutil extend_path
    init_file = nested_sub / "__init__.py"
    init_file.write_text("__path__ = __import__('pkgutil').extend_path(__path__, __name__)")

    config = Config(
        src_paths=(tmp_path,),
        auto_identify_namespace_packages=True
    )
    res = _src_path("ns.sub", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

def test_src_path_is_module_or_package_or_src_path_is_module(tmp_path):
    # Tests _src_path_is_module
    sub = tmp_path / "mymodule"
    sub.mkdir()
    (sub / "__init__.py").write_text("")

    config = Config(src_paths=(sub,))
    # root_module_name = "mymodule", src_path = sub. src_path.name == root_module_name.
    # _src_path_is_module(src_path, root_module_name) should be True.
    res = _src_path("mymodule", config)
    assert res == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {sub}.")
