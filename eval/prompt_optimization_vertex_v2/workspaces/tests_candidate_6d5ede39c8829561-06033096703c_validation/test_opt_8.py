# file: src\sample_repo\isort\isort\api.py:138-238
# asked: {"lines": [138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 180, 181, 182, 183, 185, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 164], [163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [201, 206], [208, 209], [208, 211], [222, 223], [222, 238], [228, 229], [228, 230], [230, 231], [230, 235], [235, 236], [235, 238]]}
# gained: {"lines": [138, 141, 143, 144, 145, 146, 162, 163, 187, 188, 189, 190, 192, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 208, 209, 211, 212, 213, 214, 215, 216, 217, 219, 220, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 235, 236, 238], "branches": [[163, 187], [189, 190], [189, 192], [194, 195], [194, 211], [199, 200], [199, 201], [201, 202], [208, 209], [208, 211], [222, 223], [228, 229], [228, 230], [230, 231], [235, 236], [235, 238]]}

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


class UnreadableStringIO(StringIO):
    def readable(self) -> bool:
        return False








def test_sort_stream_file_skip_setting(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda self: True)
    skipped_file = Path("skipped.py")
    
    config = Config(skip=[skipped_file.name])
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()

    with pytest.raises(FileSkipSetting):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            file_path=skipped_file,
            config=config,
        )


def test_sort_stream_atomic_existing_syntax_error():
    input_stream = StringIO("def invalid syntax")
    output_stream = StringIO()
    config = Config(atomic=True)

    with pytest.raises(ExistingSyntaxErrors):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
            config=config,
        )


def test_sort_stream_atomic_cython_syntax_error_ignored():
    input_stream = StringIO("cdef int x = 1\n")
    output_stream = StringIO()
    config = Config(atomic=True, verbose=True)

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        extension="pyx",
        config=config,
    )
    assert isinstance(changed, bool)


def test_sort_stream_unreadable_output_stream_atomic():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = UnreadableStringIO()
    config = Config(atomic=True)

    changed = sort_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        config=config,
    )
    assert changed is True


def test_sort_stream_file_skip_comment():
    input_stream = StringIO("# isort: skip_file\nimport b\nimport a\n")
    output_stream = StringIO()

    with pytest.raises(FileSkipComment):
        sort_stream(
            input_stream=input_stream,
            output_stream=output_stream,
        )


def test_sort_stream_atomic_introduced_syntax_error():
    input_stream = StringIO("import b\nimport a\n")
    output_stream = StringIO()
    config = Config(atomic=True)

    class DummyCoreProcess:
        @staticmethod
        def process(input_stream, output_stream, **kwargs):
            output_stream.write("def invalid syntax:")
            return True

    import isort.api
    original_process = isort.api.core.process
    isort.api.core.process = DummyCoreProcess.process
    try:
        with pytest.raises(IntroducedSyntaxErrors):
            sort_stream(
                input_stream=input_stream,
                output_stream=output_stream,
                config=config,
            )
    finally:
        isort.api.core.process = original_process
