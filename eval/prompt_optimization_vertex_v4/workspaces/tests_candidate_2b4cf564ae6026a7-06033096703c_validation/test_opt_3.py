# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

import pytest
from pathlib import Path
from isort.place import _is_namespace_package

def test_is_namespace_package_not_a_package(tmp_path: Path):
    # If path is not a package (_is_package returns False), returns False (line 114-115)
    file_path = tmp_path / "not_a_dir.py"
    file_path.write_text("")
    assert _is_namespace_package(file_path, frozenset(["py"])) is False

def test_is_namespace_package_no_init_with_src_files(tmp_path: Path):
    # Package without __init__.py, but contains source files or setup.cfg/pyproject.toml -> filenames is non-empty -> returns False
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "module.py").write_text("")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg_dir, src_extensions) is False

def test_is_namespace_package_no_init_no_src_files(tmp_path: Path):
    # Package without __init__.py, and no source files or setup.cfg/pyproject.toml -> filenames is empty -> returns True (line 140)
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    # empty directory, so iterdir has no matching files
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg_dir, src_extensions) is True

def test_is_namespace_package_with_init_missing_declaration(tmp_path: Path):
    # Package with __init__.py, but missing required declaration strings -> returns False (line 139)
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(b"# normal init file without declaration")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg_dir, src_extensions) is False

@pytest.mark.parametrize(
    "declaration",
    [
        b"__import__('pkg_resources').declare_namespace(__name__)",
        b'__import__("pkg_resources").declare_namespace(__name__)',
        b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        b'__path__ = __import__("pkgutil").extend_path(__path__, __name__)',
    ],
)
def test_is_namespace_package_with_init_valid_declarations(tmp_path: Path, declaration: bytes):
    # Package with __init__.py containing one of the valid namespace package declarations -> returns True (line 140)
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(declaration)
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg_dir, src_extensions) is True
