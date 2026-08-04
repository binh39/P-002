# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
from isort import sections
from isort.settings import Config
from isort.place import _src_path


def test_src_path_all_branches(tmp_path: Path):
    # Setup directories and files
    # 1. src_path where src_path.name == root_module_name and not module_path.is_dir()
    # 2. nested module triggering namespace package check (both explicit config and auto_identify)
    # 3. standard module or package or _src_path_is_module matching
    # 4. Fallback returning None

    base = tmp_path / "project"
    base.mkdir()

    # Create a structure for testing:
    # base/pkg/mod.py
    # base/pkg_auto/subpkg/mod.py
    # base/just_a_dir (where dir name == root module)
    
    pkg = base / "pkg"
    pkg.mkdir()
    mod_file = pkg / "mod.py"
    mod_file.write_text("x = 1")

    just_a_dir = base / "rootdir"
    just_a_dir.mkdir()
    # inside just_a_dir, we put a file so it acts as a module or we test src_path.name == root_module_name
    (base / "rootdir.py").write_text("y = 2")

    config = Config(src_paths=(base,))

    # Test 1: src_path.name == root_module_name and not prefix and not module_path.is_dir()
    # Let name = "rootdir" and src_paths = [base / "rootdir"] where base / "rootdir" has name == "rootdir"
    # Wait, in the code:
    # src_path = base / "rootdir"
    # root_module_name = "rootdir"
    # module_path = (src_path / root_module_name) -> base / "rootdir" / "rootdir" (not a dir)
    # src_path.name == root_module_name is True -> module_path becomes src_path.resolve()
    res1 = _src_path("rootdir", config, src_paths=[base / "rootdir"])
    assert res1 is not None
    assert res1[0] == sections.FIRSTPARTY

    # Test 2: nested_module and namespace in config.namespace_packages
    ns_base = tmp_path / "ns_project"
    ns_base.mkdir()
    sub = ns_base / "mynamespace" / "sub"
    sub.mkdir(parents=True)
    (sub / "file.py").write_text("z = 3")

    config_ns = Config(src_paths=(ns_base,), namespace_packages=["mynamespace"])
    res2 = _src_path("mynamespace.sub.file", config_ns)
    # This should recursively call _src_path and eventually find the file or package
    # Let's check how nested_module unwinds.
    # name = "mynamespace.sub.file"
    # root = "mynamespace", nested = ["sub.file"]
    # namespace = "mynamespace" in namespace_packages -> recurses with nested_module[0] = "sub.file"
    # Next: root = "sub", nested = ["file"]
    # namespace = "mynamespace.sub" ... wait, namespace becomes "mynamespace.sub"
    # If "mynamespace.sub" is not in namespace_packages, but auto_identify_namespace_packages is True...
    
    config_auto = Config(src_paths=(ns_base,), auto_identify_namespace_packages=True)
    res3 = _src_path("mynamespace.sub.file", config_auto)
    assert res3 is not None

    # Test 3: Standard module/package check
    res4 = _src_path("pkg.mod", config)
    assert res4 is not None
    assert res4[0] == sections.FIRSTPARTY

    # Test 4: Returns None when nothing matches
    res5 = _src_path("nonexistent.module", config)
    assert res5 is None
