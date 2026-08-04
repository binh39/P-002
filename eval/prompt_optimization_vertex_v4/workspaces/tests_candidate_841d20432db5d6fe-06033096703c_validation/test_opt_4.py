# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
import pytest
from isort import sections
from isort.place import _src_path
from isort.settings import Config


def test_src_path_none_src_paths(tmp_path):
    # Tests line 70-71: if src_paths is None: src_paths = config.src_paths
    config = Config(src_paths=[tmp_path])
    res = _src_path("nonexistent", config, src_paths=None)
    assert res is None


def test_src_path_special_prefix_condition(tmp_path):
    # Tests lines 79-80: if not prefix and not module_path.is_dir() and src_path.name == root_module_name: module_path = src_path.resolve()
    # Also tests line 92-94 via _src_path_is_module returning True
    sub = tmp_path / "foo"
    sub.mkdir()
    config = Config()
    res = _src_path("foo", config, src_paths=[sub])
    assert res is not None
    assert res[0] == sections.FIRSTPARTY


def test_src_path_namespace_package_explicit(tmp_path):
    # Tests lines 81-88: nested_module and namespace in config.namespace_packages -> recursive _src_path
    parent = tmp_path / "parent"
    parent.mkdir()
    child = parent / "child"
    child.mkdir()
    # Create a module inside child so that the recursive call hits module detection
    (child / "mod.py").write_text("x = 1")

    config = Config(namespace_packages=["parent.child"])
    res = _src_path("parent.child.mod", config, src_paths=[tmp_path])
    assert res is not None
    assert res[0] == sections.FIRSTPARTY


def test_src_path_namespace_package_auto_identify(tmp_path):
    # Tests lines 81-88 via auto_identify_namespace_packages and _is_namespace_package
    parent = tmp_path / "parent"
    parent.mkdir()
    child = parent / "child"
    child.mkdir()
    # A directory without __init__.py and without source files/pyproject.toml is identified as a namespace package
    (child / "mod.py").write_text("x = 1")

    config = Config(auto_identify_namespace_packages=True)
    res = _src_path("parent.child.mod", config, src_paths=[tmp_path])
    assert res is not None
    assert res[0] == sections.FIRSTPARTY


def test_src_path_is_module_or_package(tmp_path):
    # Tests lines 89-94: _is_module or _is_package
    mod = tmp_path / "mymod.py"
    mod.write_text("x = 1")

    config = Config()
    res = _src_path("mymod", config, src_paths=[tmp_path])
    assert res is not None
    assert res[0] == sections.FIRSTPARTY

    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("x = 1")
    res2 = _src_path("mypkg", config, src_paths=[tmp_path])
    assert res2 is not None
    assert res2[0] == sections.FIRSTPARTY


def test_src_path_returns_none(tmp_path):
    # Tests line 96: return None after loop finishes
    config = Config()
    res = _src_path("completely.missing.module", config, src_paths=[tmp_path])
    assert res is None
