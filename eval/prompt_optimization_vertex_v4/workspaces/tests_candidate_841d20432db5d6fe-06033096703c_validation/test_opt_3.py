# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
import pytest
from isort.place import _is_namespace_package

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

def test_is_namespace_package_not_a_package(temp_dir):
    # If path is not a package (e.g. non-existent or a file), _is_package returns False
    not_a_dir = temp_dir / "non_existent"
    assert _is_namespace_package(not_a_dir, frozenset(["py"])) is False

def test_is_namespace_package_no_init_with_source_files(temp_dir):
    # __init__.py does not exist, but there is a file with a matching src_extension
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "module.py").write_text("print('hello')")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is False

def test_is_namespace_package_no_init_with_config_file(temp_dir):
    # __init__.py does not exist, but there is a setup.cfg or pyproject.toml
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "pyproject.toml").write_text("[tool.isort]")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is False

def test_is_namespace_package_no_init_no_source_or_config(temp_dir):
    # __init__.py does not exist, and no matching files/configs -> True (implicit namespace package)
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    (pkg_dir / "README.md").write_text("docs")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

def test_is_namespace_package_with_init_missing_declaration(temp_dir):
    # __init__.py exists, but lacks pkg_resources or pkgutil declarations -> False
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("x = 1")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is False

def test_is_namespace_package_with_init_pkg_resources_single_quotes(temp_dir):
    # __init__.py exists with single quotes pkg_resources declaration -> True
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("__import__('pkg_resources').declare_namespace(__name__)")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

def test_is_namespace_package_with_init_pkg_resources_double_quotes(temp_dir):
    # __init__.py exists with double quotes pkg_resources declaration -> True
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py>".rstrip(">")
    init_file.write_text('__import__("pkg_resources").declare_namespace(__name__)')
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

def test_is_namespace_package_with_init_pkgutil_single_quotes(temp_dir):
    # __init__.py exists with single quotes pkgutil declaration -> True
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("__path__ = __import__('pkgutil').extend_path(__path__, __name__)")
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True

def test_is_namespace_package_with_init_pkgutil_double_quotes(temp_dir):
    # __init__.py exists with double quotes pkgutil declaration -> True
    pkg_dir = temp_dir / "pkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text('__path__ = __import__("pkgutil").extend_path(__path__, __name__)')
    
    assert _is_namespace_package(pkg_dir, frozenset(["py"])) is True
