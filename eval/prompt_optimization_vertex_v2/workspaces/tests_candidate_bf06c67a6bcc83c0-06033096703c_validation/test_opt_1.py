# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
import tempfile
import pytest

from isort.place import _is_namespace_package


def test_is_namespace_package_not_a_package():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Pass a non-existent path or file path so _is_package returns False
        non_pkg = tmp_path / "non_existent"
        assert _is_namespace_package(non_pkg, frozenset(["py"])) is False


def test_is_namespace_package_no_init_with_src_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create a source file so filenames is non-empty
        (tmp_path / "module.py").write_text("print('hello')")
        
        # _is_package needs to return True (it's an existing directory)
        # init_file does not exist, filenames is non-empty -> returns False
        assert _is_namespace_package(tmp_path, frozenset(["py"])) is False


def test_is_namespace_package_no_init_no_src_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # No __init__.py, no src extensions or config files -> filenames is empty -> proceeds to return True
        assert _is_namespace_package(tmp_path, frozenset(["py"])) is True


def test_is_namespace_package_with_init_missing_declaration():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        init_file = tmp_path / "__init__.py"
        init_file.write_text("# regular init file without namespace declarations")
        
        # init_file exists, but file_start does not contain required strings -> returns False
        assert _is_namespace_package(tmp_path, frozenset(["py"])) is False


@pytest.mark.parametrize(
    "declaration",
    [
        "__import__('pkg_resources').declare_namespace(__name__)",
        '__import__("pkg_resources").declare_namespace(__name__)',
        "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        '__path__ = __import__("pkgutil").extend_path(__path__, __name__)',
    ],
)
def test_is_namespace_package_with_init_valid_declarations(declaration):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        init_file = tmp_path / "__init__.py"
        init_file.write_text(declaration)
        
        # init_file exists and contains a valid declaration -> returns True
        assert _is_namespace_package(tmp_path, frozenset(["py"])) is True
