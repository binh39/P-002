# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
import pytest
from isort.place import _is_namespace_package

def test_is_namespace_package_not_a_package(tmp_path: Path):
    # _is_package(path) returns False (e.g. non-existent path or file)
    non_existent = tmp_path / "non_existent"
    assert _is_namespace_package(non_existent, frozenset(["py"])) is False

def test_is_namespace_package_init_not_exists_with_filenames(tmp_path: Path):
    # init_file does not exist, but there are source/config files inside
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "module.py").write_text("print('hello')")
    
    # Should return False because filenames is non-empty
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is False

def test_is_namespace_package_init_not_exists_no_filenames(tmp_path: Path):
    # init_file does not exist, and no matching filenames inside
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    # empty or only non-matching files
    (pkg_dir / "data.txt").write_text("some data")
    
    # Should return True because filenames is empty
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

def test_is_namespace_package_init_exists_valid_declaration(tmp_path: Path):
    # init_file exists and contains a valid namespace declaration
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

    # Test pkg_resources single quote variant
    init_file.write_bytes(b"__import__('pkg_resources').declare_namespace(__name__)")
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

    # Test pkg_resources double quote variant
    init_file.write_bytes(b'__import__("pkg_resources").declare_namespace(__name__)')
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

    # Test pkgutil double quote variant
    init_file.write_bytes(b'__path__ = __import__("pkgutil").extend_path(__path__, __name__)')
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

def test_is_namespace_package_init_exists_invalid_content(tmp_path: Path):
    # init_file exists but lacks required namespace declaration lines
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(b"x = 1")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is False
