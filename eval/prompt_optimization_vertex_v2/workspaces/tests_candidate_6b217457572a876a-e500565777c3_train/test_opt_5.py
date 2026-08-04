# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

from io import StringIO
import tempfile
import os
import pytest
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(capsys, monkeypatch):
    stream = StringIO("import os\nimport sys.path\n")
    identify_imports_main(argv=["-", "--top-only", "--follow-links", "--unique"], stdin=stream)
    captured = capsys.readouterr()
    assert "os" in captured.out

def test_identify_imports_main_files_package(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        p = os.path.join(tmpdir, "test_file.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("import os.path\n")
        identify_imports_main(argv=[p, "--packages"])
        captured = capsys.readouterr()
        assert "os" in captured.out

def test_identify_imports_main_files_module(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        p = os.path.join(tmpdir, "test_file.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("import os.path\n")
        identify_imports_main(argv=[p, "--modules"])
        captured = capsys.readouterr()
        assert "os.path" in captured.out

def test_identify_imports_main_files_attribute(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        p = os.path.join(tmpdir, "test_file.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("from os import path\n")
        identify_imports_main(argv=[p, "--attributes"])
        captured = capsys.readouterr()
        assert "os.path" in captured.out
