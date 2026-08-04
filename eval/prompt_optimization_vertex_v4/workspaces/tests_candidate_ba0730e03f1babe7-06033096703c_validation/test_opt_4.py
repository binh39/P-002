# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

import pytest
from pathlib import Path
from isort.place import _is_namespace_package


def test_is_namespace_package_not_a_package(tmp_path):
    # Line 115: not _is_package(path) -> returns False
    not_a_dir = tmp_path / "not_a_dir.txt"
    not_a_dir.write_text("hello")
    assert _is_namespace_package(not_a_dir, frozenset(["py"])) is False


def test_is_namespace_package_no_init_with_matching_filenames(tmp_path):
    # Lines 118-126: init_file does not exist, but there are matching source files / setup.cfg / pyproject.toml -> returns False
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    # Create a file matching src_extensions (.py)
    (pkg / "module.py").write_text("x = 1")

    assert _is_namespace_package(pkg, frozenset(["py"])) is False


def test_is_namespace_package_no_init_with_config_file(tmp_path):
    # Lines 118-126: init_file does not exist, but pyproject.toml exists -> returns False
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "pyproject.toml").write_text("[tool.isort]")

    assert _is_namespace_package(pkg, frozenset(["py"])) is False


def test_is_namespace_package_no_init_no_matching_filenames(tmp_path):
    # Lines 118-126 (else branch where filenames is empty) and line 140 -> returns True
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    # Create a file that doesn't match src_extensions and isn't config
    (pkg / "README.md").write_text("hello")

    assert _is_namespace_package(pkg, frozenset(["py"])) is True


def test_is_namespace_package_with_init_missing_declaration(tmp_path):
    # Lines 129-139: init_file exists, but lacks pkg_resources/pkgutil declaration -> returns False
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text("# regular init")

    assert _is_namespace_package(pkg, frozenset(["py"])) is False


def test_is_namespace_package_with_init_pkg_resources_single_quotes(tmp_path):
    # Lines 129-140: init_file has pkg_resources declare_namespace with single quotes -> returns True
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text("__import__('pkg_resources').declare_namespace(__name__)")

    assert _is_namespace_package(pkg, frozenset(["py"])) is True


def test_is_namespace_package_with_init_pkg_resources_double_quotes(tmp_path):
    # Lines 129-140: init_file has pkg_resources declare_namespace with double quotes -> returns True
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text('__import__("pkg_resources").declare_namespace(__name__)')

    assert _is_namespace_package(pkg, frozenset(["py"])) is True


def test_is_namespace_package_with_init_pkgutil_single_quotes(tmp_path):
    # Lines 129-140: init_file has pkgutil extend_path with single quotes -> returns True
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text("__path__ = __import__('pkgutil').extend_path(__path__, __name__)")

    assert _is_namespace_package(pkg, frozenset(["py"])) is True


def test_is_namespace_package_with_init_pkgutil_double_quotes(tmp_path):
    # Lines 129-140: init_file has pkgutil extend_path with double quotes -> returns True
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    init_file.write_text('__path__ = __import__("pkgutil").extend_path(__path__, __name__)')

    assert _is_namespace_package(pkg, frozenset(["py"])) is True
