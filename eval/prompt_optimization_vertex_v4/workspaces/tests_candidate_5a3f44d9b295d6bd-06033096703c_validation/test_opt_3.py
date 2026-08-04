# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

import pytest
from pathlib import Path
from isort.place import _is_namespace_package

def test_is_namespace_package_not_a_package(tmp_path: Path):
    # Line 115: not _is_package(path) -> returns False
    non_existent = tmp_path / "does_not_exist"
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(non_existent, src_extensions) is False

def test_is_namespace_package_init_missing_with_filenames(tmp_path: Path):
    # Line 119: not init_file.exists() is True
    # Line 120-125: filenames list has matching files (src_extensions or setup.cfg/pyproject.toml)
    # Line 126-127: if filenames -> returns False
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    # Create a source file inside without __init__.py
    (pkg_dir / "module.py").write_text("print('hello')", encoding="utf-8")
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is False

def test_is_namespace_package_init_missing_no_filenames(tmp_path: Path):
    # Line 119: not init_file.exists() is True
    # Line 120-125: filenames list is empty
    # Line 126-127: if filenames -> False block skipped
    # Line 140: returns True
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is True

def test_is_namespace_package_init_exists_missing_declarations(tmp_path: Path):
    # Line 119: init_file.exists() is True -> goes to else (Line 129)
    # Lines 131-138: declarations are NOT in file_start -> condition true -> returns False (Line 139)
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(b"# Just a regular init file")
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is False

@pytest.mark.parametrize(
    "content",
    [
        b"__import__('pkg_resources').declare_namespace(__name__)",
        b'__import__("pkg_resources").declare_namespace(__name__)',
        b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        b'__path__ = __import__("pkgutil").extend_path(__path__, __name__)',
    ],
)
def test_is_namespace_package_init_exists_with_declarations(tmp_path: Path, content: bytes):
    # Line 119: init_file.exists() is True -> else (Line 129)
    # Lines 131-138: declarations ARE in file_start -> condition false -> returns True (Line 140)
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    init_file = pkg_dir / "__init__.py"
    init_file.write_bytes(content)
    src_extensions = frozenset({"py"})
    assert _is_namespace_package(pkg_dir, src_extensions) is True
