# file: src\sample_repo\isort\isort\place.py:64-96
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}
# gained: {"lines": [64, 67, 68, 69, 70, 71, 73, 74, 75, 77, 78, 79, 80, 81, 82, 84, 85, 88, 90, 91, 92, 94, 96], "branches": [[70, 71], [70, 73], [77, 78], [77, 96], [79, 80], [79, 81], [81, 88], [81, 89], [89, 77], [89, 94]]}

from pathlib import Path
import tempfile
from isort.settings import Config
from isort.place import _src_path
from isort import sections

def test_src_path_default_src_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        d = tmp_path / "my_module.py"
        d.write_text("x = 1")
        config = Config(src_paths=(tmp_path,))
        result = _src_path("my_module", config, src_paths=None)
        assert result is not None
        assert result[0] == sections.FIRSTPARTY

def test_src_path_root_module_name_equals_src_path_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub = tmp_path / "foo"
        sub.mkdir()
        (sub / "__init__.py").write_text("")
        
        result = _src_path("foo", config=Config(), src_paths=(sub,))
        assert result is not None
        assert result[0] == sections.FIRSTPARTY

def test_src_path_namespace_package_explicit():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub = tmp_path / "pkg" / "subpkg"
        sub.mkdir(parents=True)
        
        config = Config(namespace_packages=("pkg",))
        (sub / "mod.py").write_text("")
        
        result = _src_path("pkg.subpkg.mod", config, src_paths=(tmp_path,))
        assert result is not None
        assert result[0] == sections.FIRSTPARTY

def test_src_path_namespace_package_auto_identify():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sub = tmp_path / "pkg" / "subpkg"
        sub.mkdir(parents=True)
        (sub / "mod.py").write_text("")

        config = Config(auto_identify_namespace_packages=True)
        result = _src_path("pkg.subpkg.mod", config, src_paths=(tmp_path,))
        assert result is not None
        assert result[0] == sections.FIRSTPARTY

def test_src_path_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = Config(src_paths=(tmp_path,))
        result = _src_path("nonexistent.module", config)
        assert result is None
