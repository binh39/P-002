# file: sample_repo\isort\isort\main.py:76-117
# asked: {"lines": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 94, 95, 96, 97, 98, 99, 100, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117], "branches": [[87, 88], [87, 94], [109, 110], [109, 111]]}
# gained: {"lines": [76, 79, 80, 81, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 94, 95, 96, 97, 98, 99, 100, 102, 105, 108, 109, 110, 111], "branches": [[87, 88], [87, 94], [109, 110]]}

import pytest
from isort import api
from isort.exceptions import FileSkipped, ISortError, UnsupportedEncoding
from isort.settings import Config
from isort.main import sort_imports

class MockConfig:
    verbose = True

def test_sort_imports_check_file_skipped(monkeypatch):
    def mock_check_file(file_name, config, **kwargs):
        raise FileSkipped("File skipped", file_name)

    monkeypatch.setattr(api, "check_file", mock_check_file)
    config = MockConfig()
    result = sort_imports("test_file.py", config, check=True)
    assert result is not None
    assert result.incorrectly_sorted is False
    assert result.skipped is True

def test_sort_imports_unsupported_encoding(monkeypatch):
    def mock_sort_file(file_name, config, **kwargs):
        raise UnsupportedEncoding(file_name)

    monkeypatch.setattr(api, "sort_file", mock_sort_file)
    config = MockConfig()
    result = sort_imports("test_file.py", config)
    assert result is not None
    assert result.incorrectly_sorted is False
    assert result.skipped is False
