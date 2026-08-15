from io import StringIO

from isort.core import process
from isort.exceptions import FileSkipComment
from isort.settings import Config


def run_process(source: str, **config_options):
    output = StringIO()
    changed = process(
        StringIO(source),
        output,
        config=Config(**config_options),
    )
    return changed, output.getvalue()


def test_process_sorts_a_basic_import_block():
    changed, output = run_process("import zebra\nimport alpha\n")

    assert changed is True
    assert output == "import alpha\nimport zebra\n"


def test_process_keeps_an_already_sorted_block():
    changed, output = run_process("import alpha\nimport zebra\n")

    assert changed is False
    assert output == "import alpha\nimport zebra\n"


def test_process_respects_skip_file_comment():
    source = "# isort: skip_file\nimport zebra\nimport alpha\n"

    try:
        run_process(source)
    except FileSkipComment:
        pass
    else:
        raise AssertionError("process() should raise FileSkipComment")
