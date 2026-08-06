import io
import zipfile

import pytest

from src.core.errors import AppError
from src.modules.experiments.executor import DockerCoverUpExecutor


def archive(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for name, content in entries.items():
            bundle.writestr(name, content)
    return output.getvalue()


def executor(max_files: int = 2, max_bytes: int = 100) -> DockerCoverUpExecutor:
    return DockerCoverUpExecutor("unused", 1, 512, 1, max_files, max_bytes)


def test_archive_rejects_too_many_files(tmp_path):
    with pytest.raises(AppError) as error:
        executor()._extract_archive(archive({"a.py": b"", "b.py": b"", "c.py": b""}), tmp_path)
    assert error.value.code == "TOO_MANY_ARCHIVE_FILES"


def test_archive_rejects_uncompressed_size_limit(tmp_path):
    with pytest.raises(AppError) as error:
        executor(max_bytes=2)._extract_archive(archive({"a.py": b"123"}), tmp_path)
    assert error.value.code == "RUNNER_ARCHIVE_TOO_LARGE"


def test_archive_rejects_path_traversal(tmp_path):
    with pytest.raises(AppError) as error:
        executor()._extract_archive(archive({"../escape.py": b"pass"}), tmp_path)
    assert error.value.code == "INVALID_ZIP"
