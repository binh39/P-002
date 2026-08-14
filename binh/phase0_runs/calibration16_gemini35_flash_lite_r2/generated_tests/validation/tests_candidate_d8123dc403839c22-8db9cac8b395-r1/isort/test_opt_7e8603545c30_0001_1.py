# file: src\sample_repo\isort\isort\main.py:75-116
# asked: {"lines": [75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116], "branches": [[86, 87], [86, 93], [108, 109], [108, 110]]}
# gained: {"lines": [75, 78, 79, 80, 83, 84, 85, 86, 87, 88, 89, 90, 91, 93, 94, 95, 96, 97, 98, 99, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116], "branches": [[86, 87], [86, 93], [108, 109], [108, 110]]}

import pytest
from unittest.mock import patch
from isort.main import sort_imports
from isort.settings import Config
from isort.exceptions import FileSkipped, UnsupportedEncoding, ISortError


def test_sort_imports_check_success(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")
    config = Config()
    attempt = sort_imports(str(p), config=config, check=True)
    assert attempt.incorrectly_sorted is True
    assert attempt.skipped is False
    assert attempt.supported_encoding is True


def test_sort_imports_check_file_skipped(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config()
    with patch("isort.api.check_file", side_effect=FileSkipped("skipped", str(p))):
        attempt = sort_imports(str(p), config=config, check=True)
        assert attempt.skipped is True
        assert attempt.supported_encoding is True


def test_sort_imports_sort_file_success(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")
    config = Config()
    attempt = sort_imports(str(p), config=config, check=False)
    # When sort_file successfully fixes the file, it returns True.
    # sort_imports does: incorrectly_sorted = not api.sort_file(...)
    # Therefore, if sort_file returns True (successfully sorted), incorrectly_sorted becomes False.
    assert attempt.incorrectly_sorted is False
    assert attempt.skipped is False
    assert attempt.supported_encoding is True


def test_sort_imports_sort_file_skipped(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config()
    with patch("isort.api.sort_file", side_effect=FileSkipped("skipped", str(p))):
        attempt = sort_imports(str(p), config=config, check=False)
        assert attempt.skipped is True
        assert attempt.supported_encoding is True


@pytest.mark.parametrize("exc", [OSError("os error"), ValueError("value error")])
def test_sort_imports_os_value_error(tmp_path, exc):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config()
    with patch("isort.api.sort_file", side_effect=exc):
        result = sort_imports(str(p), config=config)
        assert result is None


def test_sort_imports_unsupported_encoding_verbose(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config(verbose=True)
    with patch("isort.api.sort_file", side_effect=UnsupportedEncoding("bad encoding")):
        attempt = sort_imports(str(p), config=config)
        assert attempt.supported_encoding is False


def test_sort_imports_unsupported_encoding_non_verbose(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config(verbose=False)
    with patch("isort.api.sort_file", side_effect=UnsupportedEncoding("bad encoding")):
        attempt = sort_imports(str(p), config=config)
        assert attempt.supported_encoding is False


def test_sort_imports_isort_error(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config()
    with patch("isort.api.sort_file", side_effect=ISortError("isort error")):
        with pytest.raises(SystemExit) as exc_info:
            sort_imports(str(p), config=config)
        assert exc_info.value.code == 1


def test_sort_imports_generic_exception(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import a\n")
    config = Config()
    with patch("isort.api.sort_file", side_effect=RuntimeError("unexpected")):
        with pytest.raises(RuntimeError, match="unexpected"):
            sort_imports(str(p), config=config)
