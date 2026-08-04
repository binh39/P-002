# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import pytest
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(capsys, monkeypatch):
    stream = io.TextIOWrapper(io.BytesIO(b"import os\nimport sys.path\n"), encoding="utf-8")
    identify_imports_main(argv=["-"], stdin=stream)
    captured = capsys.readouterr()
    assert "os" in captured.out

def test_identify_imports_main_paths_unique_package(tmp_path, capsys):
    p = tmp_path / "sample.py"
    p.write_text("import os.path\nimport sys\n")
    identify_imports_main(argv=["--packages", str(p)])
    captured = capsys.readouterr()
    assert "os" in captured.out
    assert "sys" in captured.out

def test_identify_imports_main_paths_unique_module(tmp_path, capsys):
    p = tmp_path / "sample.py"
    p.write_text("import os.path\n")
    identify_imports_main(argv=["--modules", str(p)])
    captured = capsys.readouterr()
    assert "os.path" in captured.out

def test_identify_imports_main_paths_unique_attribute(tmp_path, capsys):
    p = tmp_path / "sample.py"
    p.write_text("from os import path\n")
    identify_imports_main(argv=["--attributes", str(p)])
    captured = capsys.readouterr()
    assert "os.path" in captured.out

def test_identify_imports_main_paths_unique_bool_and_top_only_and_follow_links(tmp_path, capsys):
    p = tmp_path / "sample.py"
    p.write_text("import os\ndef f():\n    import sys\n")
    identify_imports_main(argv=["--unique", "--top-only", "--follow-links", str(p)])
    captured = capsys.readouterr()
    assert "os" in captured.out
    assert "sys" not in captured.out
