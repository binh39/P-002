# file: src\sample_repo\isort\isort\api.py:138-238
# asked: {"lines": [138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [201, 206], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [230, 235], [235, 236], [235, 238]]}
# gained: {"lines": [138, 141, 143, 144, 145, 146, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [235, 236], [235, 238]]}

from io import StringIO
from pathlib import Path
import pytest

from isort.api import sort_stream
from isort.exceptions import (
    ExistingSyntaxErrors,
    FileSkipComment,
    FileSkipSetting,
    IntroducedSyntaxErrors,
)
from isort.settings import Config


class UnreadableStream(StringIO):
    def readable(self) -> bool:
        return False


def test_sort_stream_basic():
    inp = StringIO("import b\nimport a\n")
    out = StringIO()
    changed = sort_stream(inp, out)
    assert changed is True
    out.seek(0)
    assert out.read() == "import a\nimport b\n"




def test_sort_stream_show_diff_stream():
    inp = StringIO("import b\nimport a\n")
    out = StringIO()
    diff_output = StringIO()
    changed = sort_stream(inp, out, show_diff=diff_output)
    assert changed is True
    diff_output.seek(0)
    assert "import a" in diff_output.read()


def test_sort_stream_file_skip_setting(monkeypatch):
    fake_path = Path("skipped.py")
    config = Config(skip=["skipped.py"])
    inp = StringIO("import b\nimport a\n")
    out = StringIO()
    with pytest.raises(FileSkipSetting):
        sort_stream(inp, out, file_path=fake_path, config=config)


def test_sort_stream_atomic_existing_syntax_error():
    inp = StringIO("invalid syntax :::")
    out = StringIO()
    config = Config(atomic=True)
    with pytest.raises(ExistingSyntaxErrors):
        sort_stream(inp, out, config=config)


def test_sort_stream_atomic_cython_existing_syntax_error_verbose():
    inp = StringIO("invalid syntax :::")
    out = StringIO()
    config = Config(atomic=True, verbose=True)
    changed = sort_stream(inp, out, extension="pyx", config=config)
    assert changed is False


def test_sort_stream_atomic_unreadable_output_stream():
    inp = StringIO("import b\nimport a\n")
    out = UnreadableStream()
    config = Config(atomic=True)
    changed = sort_stream(inp, out, config=config)
    assert changed is True
    out.seek(0)
    assert "import a\nimport b\n" in out.read()


def test_sort_stream_file_skip_comment():
    inp = StringIO("# isort: skip_file\nimport b\nimport a\n")
    out = StringIO()
    with pytest.raises(FileSkipComment):
        sort_stream(inp, out, raise_on_skip=True)


def test_sort_stream_atomic_introduced_syntax_error():
    inp = StringIO("import a\n")
    out = StringIO()
    config = Config(atomic=True)

    import isort.core

    original_process = isort.core.process

    def mock_process(input_stream, output_stream, **kwargs):
        output_stream.write("invalid syntax introduced :::")
        return True

    isort.core.process = mock_process
    try:
        with pytest.raises(IntroducedSyntaxErrors):
            sort_stream(inp, out, config=config)
    finally:
        isort.core.process = original_process


def test_sort_stream_atomic_cython_introduced_syntax_error_verbose():
    inp = StringIO("import a\n")
    out = StringIO()
    config = Config(atomic=True, verbose=True)

    import isort.core

    original_process = isort.core.process

    def mock_process(input_stream, output_stream, **kwargs):
        output_stream.write("invalid syntax introduced :::")
        return True

    isort.core.process = mock_process
    try:
        changed = sort_stream(inp, out, extension="pyx", config=config)
        assert changed is True
        out.seek(0)
        assert "invalid syntax introduced :::" in out.read()
    finally:
        isort.core.process = original_process
