# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

import pytest
from pathlib import Path
from isort.place import _is_namespace_package

def test_is_namespace_package_not_a_package(tmp_path: Path):
    # If path is not a package, _is_package returns False, so _is_namespace_package returns False immediately (line 115).
    not_a_dir = tmp_path / "not_a_dir.txt"
    not_a_dir.write_text("hello")
    assert _is_namespace_package(not_a_dir, frozenset(["py"])) is False

def test_is_namespace_package_no_init_with_src_files(tmp_path: Path):
    # _is_package is True (it's a directory).
    # init_file does not exist.
    # path.iterdir() contains a file with extension in src_extensions -> filenames is non-empty -> returns False.
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "module.py").write_text("print(1)")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is False

def test_is_namespace_package_no_init_with_setup_cfg(tmp_path: Path):
    # init_file does not exist, but contains setup.cfg -> filenames is non-empty -> returns False.
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "setup.cfg").write_text("[metadata]")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is False

def test_is_namespace_package_no_init_empty(tmp_path: Path):
    # init_file does not exist, and no source files or setup/pyproject files -> filenames is empty -> returns True.
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is True

def test_is_namespace_package_with_init_missing_declaration(tmp_path: Path):
    # init_file exists, but does not contain pkg_resources or pkgutil declarations -> returns False.
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text("# just a regular init file")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is False

def test_is_namespace_package_with_init_pkg_resources_single_quote(tmp_path: Path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text("__import__('pkg_resources').declare_namespace(__name__)")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is True

def test_is_namespace_package_with_init_pkg_resources_double_quote(tmp_path: Path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text('__import__("pkg_resources").declare_namespace(__name__)')
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is True

def test_is_namespace_package_with_init_pkgutil_single_quote(tmp_path: Path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text("__path__ = __import__('pkgutil').extend_path(__path__, __name__)")
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is True

def test_is_namespace_package_with_init_pkgutil_double_quote(tmp_path: Path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text('__path__ = __import__("pkgutil").extend_path(__path__, __name__)')
    
    src_extensions = frozenset(["py"])
    assert _is_namespace_package(pkg, src_extensions) is True
