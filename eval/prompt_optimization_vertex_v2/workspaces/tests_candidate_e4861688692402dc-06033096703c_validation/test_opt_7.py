# file: src\sample_repo\isort\isort\api.py:138-238
# asked: {"lines": [138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [201, 206], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [230, 235], [235, 236], [235, 238]]}
# gained: {"lines": [138, 141, 143, 144, 145, 146, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [235, 236], [235, 238]]}

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
from isort.settings import DEFAULT_CONFIG, Config


class UnreadableStream(StringIO):
    def readable(self) -> bool:
        return False




def test_sort_stream_show_diff_true():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        show_diff=True,
    )
    assert changed is True
    output_stream.seek(0)
    diff_output = output_stream.read()
    assert "import a" in diff_output


def test_sort_stream_show_diff_custom_stream():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    diff_stream = StringIO()

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        show_diff=diff_stream,
    )
    assert changed is True
    diff_stream.seek(0)
    assert "import a" in diff_stream.read()


def test_sort_stream_skip_setting():
    input_stream = StringIO("import a\n")
    output_stream = StringIO()
    file_path = Path("skipped_file.py")
    config = Config(skip=["skipped_file.py"])

    with pytest.raises(FileSkipSetting):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            file_path=file_path,
            config=config,
            disregard_skip=False,
        )


def test_sort_stream_atomic_syntax_error_existing():
    input_stream = StringIO("def invalid_syntax(:")
    output_stream = StringIO()
    config = Config(atomic=True)

    with pytest.raises(ExistingSyntaxErrors):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            config=config,
        )


def test_sort_stream_atomic_syntax_error_existing_cython_verbose():
    input_stream = StringIO("def invalid_syntax(:")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)

    # Should not raise ExistingSyntaxErrors because extension is in CYTHON_EXTENSIONS
    sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        extension="pyx",
        config=config,
    )




def test_sort_stream_atomic_unreadable_output_stream():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = UnreadableStream()
    config = Config(atomic=True)

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        config=config,
    )
    assert changed is True
    output_stream.seek(0)
    assert "import a\nimport b\n" in output_stream.read()


def test_sort_stream_atomic_introduced_syntax_errors():
    # Construct a scenario where core.process introduces a syntax error under atomic=True.
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    config = Config(atomic=True)

    # Monkeypatch core.process to output invalid syntax after sorting
    import isort.core

    original_process = isort.core.process

    def mock_process(inp, out, **kwargs):
        out.write("def invalid_syntax(:")
        return True

    isort.core.process = mock_process
    try:
        with pytest.raises(IntroducedSyntaxErrors):
            sort_stream(
                input_stream=input_stream,
                output_stream=output_stream,
                config=config,
            )
    finally:
        isort.core.process = original_process


def test_sort_stream_atomic_introduced_syntax_errors_cython_verbose():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)

    import isort.core

    original_process = isort.core.process

    def mock_process(inp, out, **kwargs):
        out.write("def invalid_syntax(:")
        return True

    isort.core.process = mock_process
    try:
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            extension="pyx",
            config=config,
        )
    finally:
        isort.core.process = original_process
