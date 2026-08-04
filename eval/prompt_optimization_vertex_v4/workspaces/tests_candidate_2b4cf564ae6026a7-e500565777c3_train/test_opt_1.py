# file: src\sample_repo\isort\isort\main.py:975-1058
# asked: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}
# gained: {"lines": [975, 976, 977, 978, 979, 982, 983, 985, 986, 987, 988, 989, 992, 993, 994, 995, 996, 997, 1000, 1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1012, 1013, 1015, 1016, 1017, 1018, 1020, 1021, 1023, 1024, 1025, 1026, 1028, 1029, 1032, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058], "branches": [[1035, 1036], [1035, 1043], [1050, 0], [1050, 1051], [1051, 1052], [1051, 1053], [1053, 1054], [1053, 1055], [1055, 1056], [1055, 1058]]}

import io
import sys
import pytest
from isort.main import identify_imports_main
from isort import api

def test_identify_imports_main_stdin(tmp_path, capsys):
    # Test `file_names == ["-"]` branch using a provided stdin TextIOWrapper
    d = tmp_path / "sample.py"
    d.write_text("import os\nfrom sys import path\n")
    
    stream = io.TextIOWrapper(io.BytesIO(b"import os\nfrom sys import path\n"), encoding="utf-8")
    
    # Test default print case (unique=False)
    identify_imports_main(argv=["-"], stdin=stream)
    captured = capsys.readouterr()
    assert "import os" in captured.out or "import" in captured.out

def test_identify_imports_main_paths_and_unique_options(tmp_path, capsys):
    d = tmp_path / "sample_file.py"
    d.write_text("import os.path\nfrom os import path\n")
    file_str = str(d)

    # 1. Test unique == api.ImportKey.PACKAGE (--packages)
    identify_imports_main(argv=["--packages", file_str])
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 2. Test unique == api.ImportKey.MODULE (--modules)
    identify_imports_main(argv=["--modules", file_str])
    captured = capsys.readouterr()
    assert "os" in captured.out or "os.path" in captured.out

    # 3. Test unique == api.ImportKey.ATTRIBUTE (--attributes)
    identify_imports_main(argv=["--attributes", file_str])
    captured = capsys.readouterr()
    # Might print module.attribute

    # 4. Test --unique flag (unique=True, but not an ImportKey enum)
    identify_imports_main(argv=["--unique", file_str])
    captured = capsys.readouterr()
    assert "os" in captured.out

    # 5. Test --top-only and --follow-links flags
    identify_imports_main(argv=["--top-only", "--follow-links", file_str])
    captured = capsys.readouterr()
    assert "os" in captured.out
