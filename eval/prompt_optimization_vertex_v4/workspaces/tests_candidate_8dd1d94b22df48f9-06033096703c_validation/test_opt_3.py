# file: src\sample_repo\isort\isort\place.py:114-140
# asked: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 124, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}
# gained: {"lines": [114, 115, 116, 118, 119, 120, 121, 122, 123, 126, 127, 129, 130, 132, 133, 134, 135, 136, 137, 139, 140], "branches": [[115, 116], [115, 118], [119, 120], [119, 129], [126, 127], [126, 140], [131, 139], [131, 140]]}

from pathlib import Path
import tempfile
import shutil
from isort.place import _is_namespace_package

def test_is_namespace_package_coverage():
    src_extensions = frozenset(["py"])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Test when path is not a package (_is_package returns False)
        # E.g., a file instead of a directory
        not_a_dir = tmp_path / "not_a_dir.py"
        not_a_dir.write_text("")
        assert _is_namespace_package(not_a_dir, src_extensions) is False

        # Create a valid directory package
        pkg_path = tmp_path / "mypkg"
        pkg_path.mkdir()

        # 2. Test init_file does NOT exist, but there ARE matching filenames in the directory
        # This tests lines 119 -> 120-124 -> 126 -> returns False
        src_file = pkg_path / "module.py"
        src_file.write_text("print('hello')")
        assert _is_namespace_package(pkg_path, src_extensions) is False
        src_file.unlink()

        # 3. Test init_file does NOT exist, and there are NO matching filenames in the directory
        # This tests lines 119 -> 120-124 (empty list) -> 126 (falsy) -> 129 -> falls through to return True (line 140)
        assert _is_namespace_package(pkg_path, src_extensions) is True

        # 4. Test init_file DOES exist, but does NOT contain any declare_namespace or extend_path declarations
        # This tests lines 119 (else) -> 129-130 -> 131-137 (all not in file_start) -> 139 -> returns False
        init_file = pkg_path / "__init__.py"
        init_file.write_bytes(b"# just a normal init file\n")
        assert _is_namespace_package(pkg_path, src_extensions) is False

        # 5. Test init_file DOES exist and contains valid namespace declaration (e.g. pkg_resources single quotes)
        # This tests lines 131-137 (found) -> 140 -> returns True
        init_file.write_bytes(b"__import__('pkg_resources').declare_namespace(__name__)\n")
        assert _is_namespace_package(pkg_path, src_extensions) is True

        # 6. Test init_file DOES exist and contains valid pkg_resources double quotes
        init_file.write_bytes(b'__import__("pkg_resources").declare_namespace(__name__)\n')
        assert _is_namespace_package(pkg_path, src_extensions) is True

        # 7. Test init_file DOES exist and contains valid pkgutil extend_path single quotes
        init_file.write_bytes(b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n")
        assert _is_namespace_package(pkg_path, src_extensions) is True

        # 8. Test init_file DOES exist and contains valid pkgutil extend_path double quotes
        init_file.write_bytes(b'__path__ = __import__("pkgutil").extend_path(__path__, __name__)\n')
        assert _is_namespace_package(pkg_path, src_extensions) is True
