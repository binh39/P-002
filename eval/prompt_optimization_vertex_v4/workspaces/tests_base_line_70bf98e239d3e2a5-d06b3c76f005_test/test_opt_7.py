# file: src\sample_repo\isort\isort\api.py:372-507
# asked: {"lines": [372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 400, 402, 403, 404, 405, 406, 407, 409, 411, 412, 413, 414, 415, 416, 417, 418, 420, 421, 422, 423, 426, 427, 428, 429, 431, 432, 434, 435, 436, 437, 438, 439, 440, 441, 443, 444, 445, 446, 447, 448, 449, 450, 452, 454, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 475, 476, 477, 479, 480, 481, 482, 483, 484, 485, 487, 488, 489, 490, 491, 492, 493, 494, 495, 497, 499, 500, 501, 502, 503, 504, 507], "branches": [[402, 403], [402, 411], [404, 405], [404, 411], [406, 407], [406, 409], [416, 417], [416, 426], [426, 427], [426, 479], [428, 429], [428, 431], [444, 445], [444, 468], [445, 446], [445, 463], [456, 462], [456, 463], [464, 465], [464, 468], [468, 469], [468, 475], [469, 470], [469, 472], [472, 473], [472, 475], [475, 476], [475, 507], [487, 488], [487, 497]]}
# gained: {"lines": [372, 373, 374, 376, 377, 378, 379, 380, 381, 400, 402, 403, 404, 405, 406, 409, 411, 412, 413, 414, 415, 416, 417, 418, 420, 421, 422, 423, 426, 427, 428, 429, 431, 432, 434, 435, 436, 437, 438, 439, 440, 441, 443, 444, 445, 446, 447, 448, 449, 450, 452, 454, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 475, 476, 477, 479, 480, 481, 482, 483, 484, 485, 487, 488, 489, 490, 491, 492, 493, 494, 495, 497, 499, 500, 507], "branches": [[402, 403], [402, 411], [404, 405], [406, 409], [416, 417], [416, 426], [426, 427], [426, 479], [428, 429], [428, 431], [444, 445], [445, 446], [445, 463], [456, 462], [456, 463], [464, 465], [464, 468], [468, 469], [469, 470], [469, 472], [472, 473], [475, 476], [475, 507], [487, 488]]}

from pathlib import Path
import io as python_io
import sys
from unittest.mock import patch

from isort.api import sort_file
from isort.settings import Config


def test_sort_file_config_trie(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")

    class DummyTrie:
        def search(self, filename):
            return ("dummy_info", {"verbose": True})

    # Test with config_trie and verbose
    res = sort_file(p, config_trie=DummyTrie())
    assert res is True


def test_sort_file_write_to_stdout(tmp_path, capsys):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")

    res = sort_file(p, write_to_stdout=True)
    assert res is True
    captured = capsys.readouterr()
    assert "import a" in captured.out


def test_sort_file_overwrite_in_place(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")

    config = Config(overwrite_in_place=True, quiet=False)
    # When show_diff=True with overwrite_in_place, it returns False because user isn't prompted or it handles diffing differently
    # Let's test show_diff=False or handle ask_to_apply appropriately, or just call sort_file without show_diff to get True.
    res = sort_file(p, config=config, show_diff=False)
    assert res is True
    assert "import a" in p.read_text()


def test_sort_file_ask_to_apply_reject(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")

    with patch("isort.api.ask_whether_to_apply_changes_to_file", return_value=False):
        res = sort_file(p, ask_to_apply=True)
        assert res is False


def test_sort_file_ask_to_apply_accept(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")

    with patch("isort.api.ask_whether_to_apply_changes_to_file", return_value=True):
        res = sort_file(p, ask_to_apply=True)
        assert res is True


def test_sort_file_custom_output_stream(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("import b\nimport a\n")

    out_stream = python_io.StringIO()
    res = sort_file(p, output=out_stream, show_diff=True)
    assert res is True
    out_stream.seek(0)
    assert "import a" in out_stream.read()


def test_sort_file_existing_syntax_errors(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("def invalid_syntax(\n")

    config = Config(atomic=True)
    res = sort_file(p, config=config)
    assert res is False
