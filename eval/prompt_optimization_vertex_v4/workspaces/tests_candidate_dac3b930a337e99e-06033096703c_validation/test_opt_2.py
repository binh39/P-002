# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
import pytest
from isort.place import _is_namespace_package

def test_is_namespace_package_not_package(tmp_path):
    # If not _is_package(path), returns False (line 115)
    non_existent = tmp_path / "does_not_exist"
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(non_existent, src_extensions) is False

def test_is_namespace_package_no_init_with_src_files(tmp_path):
    # init_file does not exist, but there are source files / config files -> returns False
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    # Create a file matching src_extensions
    (pkg_dir / "module.py").write_text("print('hello')")
    
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is False

def test_is_namespace_package_no_init_with_config_file(tmp_path):
    # init_file does not exist, but pyproject.toml exists -> returns False
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "pyproject.toml").write_text("[tool.isort]")
    
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is False

def test_is_namespace_package_no_init_empty_or_no_matching(tmp_path):
    # init_file does not exist, and no matching files or configs -> returns True
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "random.txt").write_text("not a source file")
    
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is True

def test_is_namespace_package_with_init_without_declare_or_extend(tmp_path):
    # init_file exists, but does not contain declare_namespace or extend_path -> returns False
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text("# just a regular init")
    
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is False

@pytest.mark.parametrize("content", [
    "__import__('pkg_resources').declare_namespace(__name__)",
    '__import__("pkg_resources").declare_namespace(__name__)',
    "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
    '__path__ = __import__("pkgutil").extend_path(__path__, __name__)',
])
def test_is_namespace_package_with_init_valid_declarations(tmp_path, content):
    # init_file exists and contains one of the recognized namespace declarations -> returns True
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_text(content)
    
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is True
