# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
import tempfile
from isort.settings import Config
from isort.place import _src_path


def test_src_path_default_src_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub = tmp_path / "mypkg"
        sub.mkdir()
        (sub / "__init__.py").write_text("")

        config = Config(src_paths=[tmp_path])
        res = _src_path("mypkg", config=config, src_paths=None)
        assert res is not None
        assert res[0] == "FIRSTPARTY"


def test_src_path_not_prefix_and_not_dir_and_src_path_name_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        pkg_dir = tmp_path / "mypkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")

        config = Config(src_paths=[pkg_dir])
        res = _src_path("mypkg", config=config)
        assert res is not None
        assert res[0] == "FIRSTPARTY"


def test_src_path_nested_module_namespace_packages():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub = tmp_path / "mynamespace" / "subpkg"
        sub.mkdir(parents=True)
        (sub / "__init__.py").write_text("")

        config = Config(
            src_paths=[tmp_path],
            namespace_packages=["mynamespace"],
        )
        res = _src_path("mynamespace.subpkg", config=config)
        assert res is not None
        assert res[0] == "FIRSTPARTY"


def test_src_path_nested_module_auto_identify_namespace_packages():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub = tmp_path / "mynamespace" / "subpkg"
        sub.mkdir(parents=True)

        config = Config(
            src_paths=[tmp_path],
            auto_identify_namespace_packages=True,
        )
        res = _src_path("mynamespace.subpkg", config=config)
        assert res is not None
        assert res[0] == "FIRSTPARTY"


def test_src_path_is_module_or_package_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mod = tmp_path / "mymod.py"
        mod.write_text("")

        config = Config(src_paths=[tmp_path])
        res = _src_path("mymod", config=config)
        assert res is not None
        assert res[0] == "FIRSTPARTY"


def test_src_path_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = Config(src_paths=[tmp_path])
        res = _src_path("nonexistent", config=config)
        assert res is None
