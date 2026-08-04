# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

import pytest
from pathlib import Path
from isort.settings import Config
from isort import sections
from isort.place import _src_path


def test_src_path_default_src_paths_and_not_found(tmp_path):
    config = Config(src_paths=[tmp_path])
    # src_paths is None -> uses config.src_paths
    # module doesn't exist anywhere -> returns None
    assert _src_path("nonexistent", config, src_paths=None) is None


def test_src_path_prefix_handling(tmp_path):
    # Test line 79-80: not prefix and not module_path.is_dir() and src_path.name == root_module_name
    # Create a directory named 'foo', and inside it a file or module
    foo_dir = tmp_path / "foo"
    foo_dir.mkdir()
    
    # Let's create a scenario where src_path.name == root_module_name
    # Config src_path is tmp_path / "foo", so src_path.name == "foo"
    config = Config(src_paths=[foo_dir])
    
    # If name is "foo", root_module_name is "foo".
    # module_path = (foo_dir / "foo").resolve() which is not a dir (does not exist).
    # Since not prefix, not module_path.is_dir(), and src_path.name == root_module_name ("foo" == "foo"),
    # module_path becomes foo_dir.resolve().
    # Then if we create a file foo_dir / "__init__.py" or similar, or test it directly.
    (foo_dir / "__init__.py").write_text("")
    
    res = _src_path("foo", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY


def test_src_path_nested_module_namespace(tmp_path):
    # Test nested_module with namespace packages
    # namespace in config.namespace_packages or auto_identify_namespace_packages
    foo_dir = tmp_path / "foo"
    foo_dir.mkdir()
    sub_dir = foo_dir / "bar"
    sub_dir.mkdir()
    (sub_dir / "baz.py").write_text("")

    config = Config(
        src_paths=[tmp_path],
        namespace_packages=["foo"],
        auto_identify_namespace_packages=False,
    )
    res = _src_path("foo.bar.baz", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY


def test_src_path_nested_module_auto_identify_namespace(tmp_path):
    foo_dir = tmp_path / "foo"
    foo_dir.mkdir()
    # Namespace package without __init__.py but with a python file inside
    (foo_dir / "bar.py").write_text("")
    
    sub_dir = foo_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "mod.py").write_text("")

    config = Config(
        src_paths=[tmp_path],
        namespace_packages=[],
        auto_identify_namespace_packages=True,
    )
    res = _src_path("foo.sub.mod", config)
    assert res is not None
    assert res[0] == sections.FIRSTPARTY


def test_src_path_is_module_or_package_checks(tmp_path):
    # Test _is_module, _is_package, and _src_path_is_module branches
    mod_file = tmp_path / "mymod.py"
    mod_file.write_text("")

    config = Config(src_paths=[tmp_path])
    
    # 1. _is_module
    assert _src_path("mymod", config) == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {tmp_path}.")

    # 2. _is_package
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    assert _src_path("mypkg", config) == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {tmp_path}.")

    # 3. _src_path_is_module
    # src_path.name == module_name and src_path.is_dir() and exists_case_sensitive
    named_src = tmp_path / "directpkg"
    named_src.mkdir()
    (named_src / "__init__.py").write_text("")
    config2 = Config(src_paths=[named_src])
    assert _src_path("directpkg", config2) == (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {named_src}.")
