# file: src\sample_repo\isort\isort\api.py:138-238
# asked: {"lines": [138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [201, 206], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [230, 235], [235, 236], [235, 238]]}
# gained: {"lines": [138, 141, 143, 144, 145, 146, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [235, 236], [235, 238]]}

from io import StringIO
from pathlib import Path
import pytest
from unittest.mock import patch

from isort.api import sort_stream
from isort.exceptions import ExistingSyntaxErrors, FileSkipComment, FileSkipSetting, IntroducedSyntaxErrors
from isort.settings import Config


class UnreadableStringIO(StringIO):
    def readable(self) -> bool:
        return False


def test_sort_stream_basic():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    changed = sort_stream(input_stream, output_stream)
    assert changed is True
    output_stream.seek(0)
    assert output_stream.read() == "import a\nimport b\n"


def test_sort_stream_show_diff():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    diff_output = StringIO()
    changed = sort_stream(input_stream, output_stream, show_diff=diff_output)
    assert changed is True
    diff_output.seek(0)
    diff_content = diff_output.read()
    assert "import a" in diff_content or "import b" in diff_content


def test_sort_stream_show_diff_stream():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    diff_output = StringIO()
    changed = sort_stream(input_stream, output_stream, show_diff=diff_output)
    assert changed is True
    diff_output.seek(0)
    assert len(diff_output.read()) > 0


def test_sort_stream_skip_setting():
    # Avoid tmp_path fixture permission issues on Windows by using a dummy Path
    p = Path("skipped.py")
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    config = Config(skip=[p.name])
    with pytest.raises(FileSkipSetting):
        sort_stream(input_stream, output_stream, file_path=p, config=config)

    # With disregard_skip=True
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    changed = sort_stream(input_stream, output_stream, file_path=p, config=config, disregard_skip=True)
    assert changed is True


def test_sort_stream_atomic_existing_syntax_error():
    input_stream = StringIO("invalid syntax here ...")
    output_stream = StringIO()
    config = Config(atomic=True)
    with pytest.raises(ExistingSyntaxErrors):
        sort_stream(input_stream, output_stream, config=config)


def test_sort_stream_atomic_cython_syntax_error():
    input_stream = StringIO("cdef int x = 1\nimport b\nimport a\n")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)
    # extension not in CYTHON_EXTENSIONS should raise ExistingSyntaxErrors unless extension is cython
    with pytest.raises(ExistingSyntaxErrors):
        sort_stream(input_stream, output_stream, extension="py", config=config)

    # Now with cython extension and verbose
    input_stream = StringIO("cdef int x = 1\nimport b\nimport a\n")
    output_stream = StringIO()
    changed = sort_stream(input_stream, output_stream, extension="pyx", config=config)
    assert isinstance(changed, bool)


def test_sort_stream_atomic_unreadable_output():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = UnreadableStringIO()
    config = Config(atomic=True)
    changed = sort_stream(input_stream, output_stream, config=config)
    assert changed is True


def test_sort_stream_file_skip_comment():
    input_stream = StringIO("# isort: skip_file\nimport b\nimport a\n")
    output_stream = StringIO()
    with pytest.raises(FileSkipComment):
        sort_stream(input_stream, output_stream)


def test_sort_stream_atomic_introduced_syntax_error():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    config = Config(atomic=True)
    
    def mock_process(inp, out, **kwargs):
        out.write("invalid syntax introduced ...")
        return True

    with patch("isort.core.process", side_effect=mock_process):
        with pytest.raises(IntroducedSyntaxErrors):
            sort_stream(input_stream, output_stream, config=config)


def test_sort_stream_atomic_cython_introduced_syntax_error():
    input_stream = StringIO("cdef int x = 1\nimport b\nimport a\n")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)

    def mock_process(inp, out, **kwargs):
        out.write("cdef int x = 1\ninvalid syntax introduced ...")
        return True

    with patch("isort.core.process", side_effect=mock_process):
        changed = sort_stream(input_stream, output_stream, extension="pyx", config=config)
        assert changed is True
