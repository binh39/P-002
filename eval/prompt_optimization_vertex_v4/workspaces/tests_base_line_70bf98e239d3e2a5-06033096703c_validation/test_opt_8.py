# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
from isort.place import _src_path
from isort.settings import Config


def test_src_path_coverage(tmp_path: Path):
    # Setup directories and files
    # 1. src_path where src_path.name == root_module_name and not prefix and not module_path.is_dir()
    my_mod_dir = tmp_path / "my_mod"
    my_mod_dir.mkdir()
    init_file = my_mod_dir / "__init__.py"
    init_file.write_text("")

    config = Config(src_paths=[my_mod_dir])

    # Case A: src_path.name == root_module_name, not prefix, module_path is not a dir (my_mod/my_mod is not a dir), but mod_file exists.
    res = _src_path("my_mod", config)
    assert res is not None
    assert res[0] == "FIRSTPARTY"

    # Case B: Nested module with namespace packages (config.namespace_packages)
    sub_dir = my_mod_dir / "sub"
    sub_dir.mkdir()
    sub_sub_dir = sub_dir / "deep"
    sub_sub_dir.mkdir()
    (sub_sub_dir / "__init__.py").write_text("")

    config_ns = Config(
        src_paths=[my_mod_dir],
        namespace_packages=["my_mod.sub"],
    )
    res_ns = _src_path("my_mod.sub.deep", config_ns)
    assert res_ns is not None
    assert res_ns[0] == "FIRSTPARTY"

    # Case C: auto_identify_namespace_packages with namespace package
    ns_pkg_dir = tmp_path / "nspkg"
    ns_pkg_dir.mkdir()
    sub_ns = ns_pkg_dir / "subns"
    sub_ns.mkdir()
    (sub_ns / "somefile.py").write_text("y = 2")

    config_auto_ns = Config(
        src_paths=[ns_pkg_dir],
        auto_identify_namespace_packages=True,
    )
    res_auto2 = _src_path("nspkg.subns", config_auto_ns)
    assert res_auto2 is not None

    # Case D: None return when nothing matches
    res_none = _src_path("nonexistent.module", config)
    assert res_none is None

    # Case E: _src_path_is_module branch
    single_dir = tmp_path / "single"
    single_dir.mkdir()
    config_single = Config(src_paths=[single_dir])
    res_single = _src_path("single", config_single)
    assert res_single is not None
    assert res_single[0] == "FIRSTPARTY"
