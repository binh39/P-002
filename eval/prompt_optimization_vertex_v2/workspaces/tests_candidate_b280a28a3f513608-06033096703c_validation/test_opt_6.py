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
from isort.settings import Config


class UnreadableStream(StringIO):
    def readable(self) -> bool:
        return False


def test_sort_stream_show_diff():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        show_diff=True,
    )
    assert changed is True
    diff_output = output_stream.getvalue()
    assert "import a" in diff_output
    assert "import b" in diff_output


def test_sort_stream_show_diff_custom_stream():
    input_stream = StringIO("import b\nimport a\n")
    diff_stream = StringIO()
    output_stream = StringIO()
    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        show_diff=diff_stream,
    )
    assert changed is True
    assert "import a" in diff_stream.getvalue()


def test_sort_stream_file_skip_setting():
    p = Path("nonexistent_file_for_skip.py")
    config = Config(skip=[str(p)])
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()

    with pytest.raises(FileSkipSetting):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            config=config,
            file_path=p,
            disregard_skip=False,
        )


def test_sort_stream_atomic_existing_syntax_error():
    input_stream = StringIO("def invalid_syntax(\n")
    output_stream = StringIO()
    config = Config(atomic=True)

    with pytest.raises(ExistingSyntaxErrors):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            config=config,
            extension="py",
        )


def test_sort_stream_atomic_existing_syntax_error_cython_verbose():
    input_stream = StringIO("def invalid_syntax(\n")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        config=config,
        extension="pyx",
    )
    assert changed is False


def test_sort_stream_atomic_unreadable_output():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = UnreadableStream()
    config = Config(atomic=True)

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        config=config,
    )
    assert changed is True
    assert "import a" in output_stream.getvalue()




def test_sort_stream_atomic_introduced_syntax_error(monkeypatch):
    from isort import core
    def mock_process(inp, out, *args, **kwargs):
        out.write("def invalid_syntax(\n")
        return True

    monkeypatch.setattr(core, "process", mock_process)
    input_stream = StringIO("import a\n")
    output_stream = StringIO()
    config = Config(atomic=True)
    file_path = Path("test_file.py")

    with pytest.raises(IntroducedSyntaxErrors):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            config=config,
            file_path=file_path,
            extension="py",
        )


def test_sort_stream_atomic_introduced_syntax_error_cython_verbose(monkeypatch):
    from isort import core
    def mock_process(inp, out, *args, **kwargs):
        out.write("def invalid_syntax(\n")
        return True

    monkeypatch.setattr(core, "process", mock_process)
    input_stream = StringIO("import a\n")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)
    file_path = Path("test_file.py")

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        config=config,
        file_path=file_path,
        extension="pyx",
    )
    assert changed is True
    assert "def invalid_syntax(" in output_stream.getvalue()
