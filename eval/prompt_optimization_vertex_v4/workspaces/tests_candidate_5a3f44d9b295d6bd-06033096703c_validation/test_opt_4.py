# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
from isort.place import _src_path
from isort.settings import Config


def test_src_path_default_src_paths(tmp_path):
    # Tests line 70: if src_paths is None: src_paths = config.src_paths
    sub = tmp_path / "my_module"
    sub.mkdir()
    (sub / "__init__.py").write_text("")

    config = Config(src_paths=[tmp_path])
    res = _src_path("my_module", config, src_paths=None)
    assert res is not None
    assert res[0] == "FIRSTPARTY"


def test_src_path_prefix_handling(tmp_path):
    # Tests lines 79-80: not prefix and not module_path.is_dir() and src_path.name == root_module_name
    # Where src_path itself IS the module (e.g. src_path named 'my_mod', module_path doesn't exist as a subdir)
    mod_dir = tmp_path / "my_mod"
    mod_dir.mkdir()
    py_file = tmp_path / "my_mod.py"
    py_file.write_text("")

    # Here src_path is mod_dir (named 'my_mod'), root_module_name is 'my_mod'
    # mod_dir / 'my_mod' is not a dir. prefix is empty. src_path.name == root_module_name.
    config = Config(src_paths=[mod_dir])
    res = _src_path("my_mod", config)
    assert res is not None


def test_src_path_namespace_packages(tmp_path):
    # Tests lines 81-88: nested_module and namespace in config.namespace_packages ... return _src_path(...)
    ns_dir = tmp_path / "mynamespace"
    ns_dir.mkdir()
    sub_mod = ns_dir / "sub"
    sub_mod.mkdir()
    (sub_mod / "__init__.py").write_text("")

    config = Config(src_paths=[tmp_path], namespace_packages=["mynamespace"])
    res = _src_path("mynamespace.sub", config)
    assert res is not None
    assert res[0] == "FIRSTPARTY"


def test_src_path_auto_identify_namespace_packages(tmp_path):
    # Tests auto_identify_namespace_packages and _is_namespace_package branch
    ns_dir = tmp_path / "autons"
    ns_dir.mkdir()
    # Namespace package without __init__.py but with submodules or files
    sub_mod = ns_dir / "sub"
    sub_mod.mkdir()
    (sub_mod / "__init__.py").write_text("")

    config = Config(src_paths=[tmp_path], auto_identify_namespace_packages=True)
    res = _src_path("autons.sub", config)
    assert res is not None


def test_src_path_is_module_or_package_or_src_path_is_module(tmp_path):
    # Tests lines 89-94: _is_module, _is_package, or _src_path_is_module returning FIRSTPARTY
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")

    config = Config(src_paths=[tmp_path])
    res = _src_path("mypkg", config)
    assert res is not None
    assert res[0] == "FIRSTPARTY"

    # Test _src_path_is_module branch specifically
    # module_name == src_path.name and src_path.is_dir() and exists_case_sensitive(str(src_path))
    config2 = Config(src_paths=[pkg_dir])
    res2 = _src_path("mypkg", config2)
    assert res2 is not None


def test_src_path_returns_none(tmp_path):
    # Tests line 96: return None when nothing matches
    config = Config(src_paths=[tmp_path])
    res = _src_path("nonexistent_module_xyz", config)
    assert res is None
