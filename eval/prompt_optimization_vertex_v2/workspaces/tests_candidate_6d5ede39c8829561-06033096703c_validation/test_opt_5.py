# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
from isort.settings import Config
from isort.place import _src_path


def test_src_path_coverage() -> None:
    # Use a fixed subdirectory path instead of pytest's tmp_path fixture
    # to avoid Windows file-locking PermissionError during pytest teardown.
    base_dir = Path(__file__).parent / ".test_src_path_tmp"
    base_dir.mkdir(exist_ok=True)

    try:
        pkg_dir = base_dir / "my_pkg"
        pkg_dir.mkdir(exist_ok=True)
        (pkg_dir / "__init__.py").write_text("")

        sub_dir = pkg_dir / "sub"
        sub_dir.mkdir(exist_ok=True)
        (sub_dir / "mod.py").write_text("")

        flat_dir = base_dir / "flat_mod"
        flat_dir.mkdir(exist_ok=True)

        config = Config(src_paths=[base_dir])

        # Test 1: src_paths is None branch (defaults to config.src_paths)
        res = _src_path("my_pkg", config, src_paths=None)
        assert res is not None
        assert res[0] == "FIRSTPARTY"

        # Test nested module with namespace packages (manual namespace package)
        config_ns = Config(src_paths=[base_dir], namespace_packages=["my_pkg"])
        res_ns = _src_path("my_pkg.sub.mod", config_ns)
        assert res_ns is not None
        assert res_ns[0] == "FIRSTPARTY"

        # Test auto_identify_namespace_packages branch
        config_auto_ns = Config(src_paths=[base_dir], auto_identify_namespace_packages=True)
        res_auto = _src_path("my_pkg.sub.mod", config_auto_ns)
        assert res_auto is not None
        assert res_auto[0] == "FIRSTPARTY"

        # Test when module_path is not a dir and src_path.name == root_module_name
        res_match_name = _src_path("my_pkg", config, src_paths=[pkg_dir])
        assert res_match_name is not None

        # Test returning None (not found)
        res_none = _src_path("nonexistent_module_xyz", config)
        assert res_none is None

    finally:
        # Clean up created test files and directories manually
        import shutil
        shutil.rmtree(base_dir, ignore_errors=True)
