import io
import stat
import zipfile

import pytest

from backend.core.errors import AppError
from backend.modules.analysis.analyzer import analyze_zip


def archive_with(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, content in entries.items():
            archive.writestr(path, content)
    return buffer.getvalue()


def test_analysis_rejects_archive_without_safe_python_files():
    archive = archive_with({"../outside.py": "def unsafe(): pass", "README.md": "docs"})

    with pytest.raises(AppError) as error:
        analyze_zip("project", archive, max_python_files=10, max_uncompressed_bytes=1024)

    assert error.value.code == "NO_PYTHON_FILES"


def test_analysis_limits_python_file_count():
    archive = archive_with({"one.py": "def one(): pass", "two.py": "def two(): pass"})

    with pytest.raises(AppError) as error:
        analyze_zip("project", archive, max_python_files=1, max_uncompressed_bytes=1024)

    assert error.value.code == "TOO_MANY_PYTHON_FILES"


def test_analysis_excludes_tests_migrations_and_build_outputs():
    archive = archive_with(
        {
            "src/package/core.py": "def target():\n    return 1\n",
            "tests/test_core.py": "def test_target():\n    assert True\n",
            "src/package/core_test.py": "def helper_test():\n    return 1\n",
            "migrations/version.py": "def upgrade():\n    return 1\n",
            "build/generated.py": "def generated():\n    return 1\n",
        }
    )

    result = analyze_zip("project", archive, max_python_files=10, max_uncompressed_bytes=4096)

    assert result.python_file_count == 1
    assert [function.qualified_name for function in result.functions] == ["target"]


def test_analysis_ignores_symbolic_links_without_materializing_them():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        link = zipfile.ZipInfo("src/package/link.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "target.py")

        archive.writestr("src/package/core.py", "def target():\n    return 1\n")

    result = analyze_zip("project", buffer.getvalue(), max_python_files=10, max_uncompressed_bytes=1024)

    assert result.python_file_count == 1
    assert result.warning_count == 1
    assert [item.qualified_name for item in result.functions] == ["target"]


def test_analysis_rejects_case_insensitive_duplicate_python_paths():
    archive = archive_with(
        {
            "src/package/core.py": "def one():\n    return 1\n",
            "SRC/PACKAGE/CORE.PY": "def two():\n    return 2\n",
        }
    )

    with pytest.raises(AppError) as error:
        analyze_zip("project", archive, max_python_files=10, max_uncompressed_bytes=1024)

    assert error.value.code == "DUPLICATE_ZIP_ENTRY"


def test_analysis_strips_the_same_single_wrapper_directory_as_runtime():
    archive = archive_with(
        {
            "PySnooper-master/pysnooper/core.py": "def target():\n    return 1\n",
            "PySnooper-master/README.md": "docs",
        }
    )

    result = analyze_zip("project", archive, max_python_files=10, max_uncompressed_bytes=4096)

    assert [function.file for function in result.functions] == ["pysnooper/core.py"]


def test_analysis_selects_python_313_from_wrapped_pyproject_metadata():
    archive = archive_with(
        {
            "project-main/pyproject.toml": '[project]\nname = "example"\nrequires-python = ">=3.13"\n',
            "project-main/src/example/core.py": "def target():\n    return 1\n",
        }
    )

    result = analyze_zip("project", archive, max_python_files=10, max_uncompressed_bytes=4096)

    assert result.requires_python == ">=3.13"
    assert result.python_version == "3.13"


def test_analysis_keeps_preferred_python_when_requirement_is_compatible():
    archive = archive_with(
        {
            "pyproject.toml": '[project]\nname = "example"\nrequires-python = ">=3.10"\n',
            "src/example/core.py": "def target():\n    return 1\n",
        }
    )

    result = analyze_zip(
        "project",
        archive,
        max_python_files=10,
        max_uncompressed_bytes=4096,
        preferred_python_version="3.12",
    )

    assert result.python_version == "3.12"


def test_analysis_rejects_requirement_without_a_deployed_python_minor():
    archive = archive_with(
        {
            "pyproject.toml": '[project]\nname = "example"\nrequires-python = ">=3.14"\n',
            "src/example/core.py": "def target():\n    return 1\n",
        }
    )

    with pytest.raises(AppError) as error:
        analyze_zip("project", archive, max_python_files=10, max_uncompressed_bytes=4096)

    assert error.value.code == "PYTHON_RUNTIME_UNAVAILABLE"
    assert "3.13" in error.value.message
