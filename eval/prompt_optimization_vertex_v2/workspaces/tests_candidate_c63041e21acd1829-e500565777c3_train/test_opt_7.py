# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import tempfile
import os
import pytest
from isort import api
from isort.main import identify_imports_main


def test_identify_imports_main_stdin(capsys):
    # Test file == ["-"], reading from stdin stream with various uniqueness flags
    stream_content = "import os\nfrom sys import path\nimport os.path\n"

    # 1. Default (str(identified_import))
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))
    identify_imports_main(argv=["-"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 2. --packages (ImportKey.PACKAGE)
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))
    identify_imports_main(argv=["-", "--packages"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 3. --modules (ImportKey.MODULE)
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))
    identify_imports_main(argv=["-", "--modules"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "sys" in captured.out

    # 4. --attributes (ImportKey.ATTRIBUTE)
    stdin_wrapper = io.TextIOWrapper(io.BytesIO(stream_content.encode("utf-8")))
    identify_imports_main(argv=["-", "--attributes"], stdin=stdin_wrapper)
    captured = capsys.readouterr()
    assert "path" in captured.out


def test_identify_imports_main_paths(capsys):
    # Test file path processing and --unique flag using standard tempfile to bypass pytest tmp_path PermissionError on Windows
    with tempfile.TemporaryDirectory() as tmpdir:
        p = os.path.join(tmpdir, "sample.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("import os\nfrom sys import path\n")

        # Call with path and --unique
        identify_imports_main(argv=[p, "--unique", "--top-only", "--follow-links"])
        captured = capsys.readouterr()
        assert "os" in captured.out
