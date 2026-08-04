# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
import pytest
from isort.place import _is_namespace_package

def test_is_namespace_package_not_package(tmp_path: Path):
    # Line 115: not _is_package(path) -> returns False
    non_existent = tmp_path / "does_not_exist"
    src_exts = frozenset({"py"})
    assert _is_namespace_package(non_existent, src_exts) is False

def test_is_namespace_package_no_init_with_source_files(tmp_path: Path):
    # Lines 118-127: init_file does not exist, but there are source files/setup.cfg/pyproject.toml -> returns False
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    # Create a source file
    (pkg_dir / "module.py").write_text("")
    src_exts = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_exts) is False

def test_is_namespace_package_no_init_no_source_files(tmp_path: Path):
    # Lines 118-126, 140: init_file does not exist, no source files -> returns True (implicit namespace package)
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    src_exts = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_exts) is True

def test_is_namespace_package_with_init_without_namespace_declaration(tmp_path: Path):
    # Lines 129-139: init_file exists, but lacks proper namespace declarations -> returns False
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("# regular init")
    src_exts = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_exts) is False

def test_is_namespace_package_with_init_with_pkg_resources(tmp_path: Path):
    # Lines 129-140: init_file has pkg_resources declare_namespace -> returns True
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(b"__import__('pkg_resources').declare_namespace(__name__)")
    src_exts = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_exts) is True

def test_is_namespace_package_with_init_with_pkgutil(tmp_path: Path):
    # Lines 129-140: init_file has pkgutil extend_path -> returns True
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)")
    src_exts = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_exts) is True
