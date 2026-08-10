import io
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
