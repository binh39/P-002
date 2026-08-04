# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
from isort.place import _is_namespace_package

def test_is_namespace_package_not_package(tmp_path):
    # Pass a path that does not exist so that exists_case_sensitive returns False (making _is_package return False).
    non_existent = tmp_path / "does_not_exist"
    assert _is_namespace_package(non_existent, frozenset(["py"])) is False

def test_is_namespace_package_init_exists_valid_pkgutil(tmp_path):
    # Case where __init__.py exists and contains extend_path
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_bytes(b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n")
    
    assert _is_namespace_package(pkg, frozenset(["py"])) is True

def test_is_namespace_package_init_exists_valid_pkg_resources(tmp_path):
    # Case where __init__.py exists and contains declare_namespace
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_bytes(b"__import__('pkg_resources').declare_namespace(__name__)\n")
    
    assert _is_namespace_package(pkg, frozenset(["py"])) is True

def test_is_namespace_package_init_exists_invalid(tmp_path):
    # Case where __init__.py exists but does NOT contain namespace declarations -> returns False
    pkg = tmp_path / "my_pkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_bytes(b"print('hello')\n")
    
    assert _is_namespace_package(pkg, frozenset(["py"])) is False

def test_is_namespace_package_complete_paths(tmp_path):
    # 1. Package with __init__.py containing valid pkgutil double quotes
    pkg1 = tmp_path / "pkg1"
    pkg1.mkdir()
    (pkg1 / "__init__.py").write_bytes(b'__path__ = __import__("pkgutil").extend_path(__path__, __name__)')
    assert _is_namespace_package(pkg1, frozenset(["py"])) is True

    # 2. Package with __init__.py containing valid pkg_resources double quotes
    pkg2 = tmp_path / "pkg2"
    pkg2.mkdir()
    (pkg2 / "__init__.py").write_bytes(b'__import__("pkg_resources").declare_namespace(__name__)')
    assert _is_namespace_package(pkg2, frozenset(["py"])) is True

    # 3. Package without __init__.py but containing source files matching extension -> filenames is non-empty -> returns False
    pkg4 = tmp_path / "pkg4"
    pkg4.mkdir()
    (pkg4 / "mod.py").write_text("")
    assert _is_namespace_package(pkg4, frozenset(["py"])) is False

    # 4. Package without __init__.py and without source files matching extension -> returns True
    pkg5 = tmp_path / "pkg5"
    pkg5.mkdir()
    assert _is_namespace_package(pkg5, frozenset(["py"])) is True

    # 5. Package without __init__.py and containing setup.cfg/pyproject.toml -> filenames is non-empty -> returns False
    pkg6 = tmp_path / "pkg6"
    pkg6.mkdir()
    (pkg6 / "pyproject.toml").write_text("")
    assert _is_namespace_package(pkg6, frozenset(["py"])) is False
