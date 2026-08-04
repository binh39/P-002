# file: src\sample_repo\isort\isort\api.py:372-507
# asked: {"lines": [372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 400, 402, 403, 404, 405, 406, 407, 409, 411, 412, 413, 414, 415, 416, 417, 418, 420, 421, 422, 423, 426, 427, 428, 429, 431, 432, 434, 435, 436, 437, 438, 439, 440, 441, 443, 444, 445, 446, 447, 448, 449, 450, 452, 454, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 475, 476, 477, 479, 480, 481, 482, 483, 484, 485, 487, 488, 489, 490, 491, 492, 493, 494, 495, 497, 499, 500, 501, 502, 503, 504, 507], "branches": [[402, 403], [402, 411], [404, 405], [404, 411], [406, 407], [406, 409], [416, 417], [416, 426], [426, 427], [426, 479], [428, 429], [428, 431], [444, 445], [444, 468], [445, 446], [445, 463], [456, 462], [456, 463], [464, 465], [464, 468], [468, 469], [468, 475], [469, 470], [469, 472], [472, 473], [472, 475], [475, 476], [475, 507], [487, 488], [487, 497]]}
# gained: {"lines": [372, 373, 374, 376, 377, 378, 379, 380, 381, 400, 402, 403, 404, 405, 406, 409, 411, 412, 413, 414, 415, 416, 417, 418, 420, 421, 422, 423, 426, 427, 428, 429, 431, 432, 434, 435, 436, 437, 438, 439, 440, 441, 443, 444, 445, 446, 447, 448, 449, 450, 452, 454, 456, 457, 458, 459, 462, 463, 464, 468, 469, 470, 471, 472, 473, 475, 476, 477, 479, 480, 481, 482, 483, 484, 485, 487, 488, 489, 490, 491, 492, 493, 494, 495, 497, 507], "branches": [[402, 403], [402, 411], [404, 405], [406, 409], [416, 417], [416, 426], [426, 427], [426, 479], [428, 429], [428, 431], [444, 445], [445, 446], [445, 463], [456, 462], [464, 468], [468, 469], [469, 470], [472, 473], [475, 476], [475, 507], [487, 488]]}

import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from isort.api import sort_file
from isort.settings import Config
from isort.exceptions import ExistingSyntaxErrors, IntroducedSyntaxErrors


@pytest.fixture
def temp_file():
    fd, path = tempfile.mkstemp(suffix=".py")
    import os
    os.close(fd)
    p = Path(path)
    p.write_text("import b\nimport a\n")
    yield p
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass


def test_sort_file_config_trie(temp_file):
    class MockTrie:
        def search(self, filename):
            return ("mock_info", {"verbose": True})

    sort_file(temp_file, config_trie=MockTrie())
    assert "import a" in temp_file.read_text()


def test_sort_file_write_to_stdout(temp_file, capsys):
    changed = sort_file(temp_file, write_to_stdout=True)
    assert changed is True




def test_sort_file_overwrite_in_place_ask_decline(temp_file):
    config = Config(overwrite_in_place=True, quiet=True)
    with patch("isort.api.ask_whether_to_apply_changes_to_file", return_value=False):
        changed = sort_file(temp_file, config=config, ask_to_apply=True)
        assert changed is False


def test_sort_file_custom_output_stream_and_show_diff(temp_file):
    out_stream = io.StringIO()
    changed = sort_file(temp_file, output=out_stream, show_diff=True, config=Config(quiet=True))
    assert changed is True
    out_stream.seek(0)
    assert "import a" in out_stream.read()


