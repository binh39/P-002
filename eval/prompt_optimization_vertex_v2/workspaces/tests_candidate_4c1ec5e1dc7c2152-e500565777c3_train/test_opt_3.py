# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import pytest
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(capsys):
    stream_content = "import os\nimport sys\n"
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))

    # 1. stdin with default unique (False)
    identify_imports_main(argv=["-"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 2. stdin with --packages
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))
    identify_imports_main(argv=["-", "--packages"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 3. stdin with --modules
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))
    identify_imports_main(argv=["-", "--modules"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 4. stdin with --attributes and --top-only and --follow-links
    stream_content_attr = "from collections import defaultdict\n"
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content_attr.encode("utf-8")))
    identify_imports_main(argv=["-", "--attributes", "--top-only", "--follow-links"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "collections.defaultdict" in captured.out


def test_identify_imports_main_paths(capsys, monkeypatch):
    # Use monkeypatch.chdir with a standard tempfile directory instead of pytest's tmp_path to avoid WinError 5 on Windows
    import tempfile
    from pathlib import Path

    temp_dir = tempfile.TemporaryDirectory()
    try:
        d = Path(temp_dir.name) / "subdir"
        d.mkdir()
        p = d / "test_file.py"
        p.write_text("import json\nfrom math import pi\n")

        # 1. Path with --unique
        identify_imports_main(argv=[str(p), "--unique"])
        captured = capsys.readouterr()
        assert "json" in captured.out

        # 2. Path with --packages
        identify_imports_main(argv=[str(p), "--packages"])
        captured = capsys.readouterr()
        assert "json" in captured.out

        # 3. Path with --modules
        identify_imports_main(argv=[str(p), "--modules"])
        captured = capsys.readouterr()
        assert "json" in captured.out

        # 4. Path with --attributes
        p_attr = d / "test_attr.py"
        p_attr.write_text("from os import path\n")
        identify_imports_main(argv=[str(p_attr), "--attributes"])
        captured = capsys.readouterr()
        assert "os.path" in captured.out
    finally:
        temp_dir.cleanup()
