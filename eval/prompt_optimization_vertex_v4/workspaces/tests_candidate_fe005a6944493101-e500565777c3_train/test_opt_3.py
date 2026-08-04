# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import pytest
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(capsys, monkeypatch):
    # Test `file_names == ["-"]` with custom stdin stream and different unique flags
    stream = io.StringIO("import os\nfrom sys import path\n")
    
    # 1. Default unique (False)
    identify_imports_main(["-"], stdin=stream)
    captured = capsys.readouterr()
    assert "os" in captured.out or "path" in captured.out

    # 2. --packages
    stream.seek(0)
    identify_imports_main(["-", "--packages"], stdin=stream)
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 3. --modules
    stream.seek(0)
    identify_imports_main(["-", "--modules"], stdin=stream)
    captured = capsys.readouterr()
    assert "sys" in captured.out

    # 4. --attributes
    stream.seek(0)
    identify_imports_main(["-", "--attributes"], stdin=stream)
    captured = capsys.readouterr()
    assert "path" in captured.out


def test_identify_imports_main_paths(tmp_path, capsys):
    # Test `file_names != ["-"]` using temporary files
    f1 = tmp_path / "test_file.py"
    f1.write_text("import collections\nfrom itertools import chain\n")

    # 1. unique = True / other options or standard files
    identify_imports_main([str(f1), "--top-only", "--follow-links", "--unique"])
    captured = capsys.readouterr()
    assert "collections" in captured.out
